#!/usr/bin/env python3
"""
Скрипт для массовой проверки контактов с множественными аккаунтами
"""

import json
import time
import requests
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import csv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

console = Console()

class BulkChecker:
    def __init__(self, api_url: str = "http://localhost:5000"):
        self.api_url = api_url
        self.results_dir = Path("bulk_results")
        self.results_dir.mkdir(exist_ok=True)
        
    def load_contacts_from_file(self, file_path: str) -> List[str]:
        """Загружает контакты из файла"""
        contacts = []
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Файл {file_path} не найден")
        
        # Определяем формат файла
        if file_path.suffix.lower() == '.csv':
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row:
                        contacts.append(row[0].strip())
        elif file_path.suffix.lower() == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        contacts.append(line)
        elif file_path.suffix.lower() == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    contacts = data
                elif isinstance(data, dict) and 'contacts' in data:
                    contacts = data['contacts']
                else:
                    raise ValueError("Неверный формат JSON файла")
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {file_path.suffix}")
        
        # Убираем дубликаты
        contacts = list(set(contacts))
        rprint(f"📊 Загружено {len(contacts)} уникальных контактов")
        return contacts
    
    def check_api_status(self) -> bool:
        """Проверяет статус API"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                rprint(f"✅ API работает: {data.get('ready_clients', 0)} аккаунтов готово")
                return True
            else:
                rprint(f"❌ API недоступен: {response.status_code}")
                return False
        except Exception as e:
            rprint(f"❌ Ошибка подключения к API: {e}")
            return False
    
    def process_contacts(self, contacts: List[str], batch_size: int = 10, 
                        save_progress: bool = True) -> Dict[str, Any]:
        """Обрабатывает список контактов батчами"""
        
        if not self.check_api_status():
            raise Exception("API недоступен")
        
        total_contacts = len(contacts)
        results = {}
        processed = 0
        errors = 0
        
        # Создаем файл для сохранения прогресса
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        progress_file = self.results_dir / f"progress_{timestamp}.json"
        
        # Загружаем предыдущий прогресс если есть
        if save_progress and progress_file.exists():
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                    results = saved_data.get('results', {})
                    processed = saved_data.get('processed', 0)
                    rprint(f"📂 Загружен предыдущий прогресс: {processed} контактов")
            except Exception as e:
                rprint(f"⚠️ Ошибка загрузки прогресса: {e}")
        
        # Определяем тип контактов (телефоны или username)
        is_phone = any('+' in contact or contact.replace(' ', '').isdigit() for contact in contacts[:10])
        endpoint = "/check_phones" if is_phone else "/check_usernames"
        field_name = "phones" if is_phone else "usernames"
        
        rprint(f"🔍 Тип контактов: {'Телефоны' if is_phone else 'Username'}")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task(
                f"Проверка контактов...", 
                total=total_contacts
            )
            
            progress.update(task, completed=processed)
            
            for i in range(processed, total_contacts, batch_size):
                batch = contacts[i:i + batch_size]
                
                try:
                    # Отправляем запрос
                    response = requests.post(
                        f"{self.api_url}{endpoint}",
                        json={field_name: batch},
                        timeout=120
                    )
                    
                    if response.status_code == 200:
                        batch_results = response.json()
                        results.update(batch_results)
                        processed += len(batch)
                        
                        # Подсчитываем ошибки
                        batch_errors = sum(1 for r in batch_results.values() if 'error' in r)
                        errors += batch_errors
                        
                        progress.update(task, completed=processed)
                        
                        # Сохраняем прогресс
                        if save_progress:
                            with open(progress_file, 'w', encoding='utf-8') as f:
                                json.dump({
                                    'results': results,
                                    'processed': processed,
                                    'total': total_contacts,
                                    'errors': errors,
                                    'timestamp': datetime.now().isoformat()
                                }, f, indent=2, ensure_ascii=False)
                        
                        # Небольшая пауза между батчами
                        time.sleep(1)
                        
                    else:
                        rprint(f"❌ Ошибка API: {response.status_code}")
                        time.sleep(5)  # Ждем больше при ошибке
                        
                except Exception as e:
                    rprint(f"❌ Ошибка обработки батча: {e}")
                    time.sleep(5)
        
        return {
            'results': results,
            'total_processed': processed,
            'total_contacts': total_contacts,
            'errors': errors,
            'success_rate': ((processed - errors) / processed * 100) if processed > 0 else 0
        }
    
    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Сохраняет результаты в файлы"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bulk_check_{timestamp}"
        
        # Сохраняем полные результаты в JSON
        json_file = self.results_dir / f"{filename}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Создаем CSV с основными данными
        csv_file = self.results_dir / f"{filename}.csv"
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            
            # Заголовки
            headers = ['contact', 'found', 'id', 'username', 'first_name', 'last_name', 
                      'premium', 'verified', 'bot', 'last_seen', 'bio', 'error']
            writer.writerow(headers)
            
            # Данные
            for contact, data in results['results'].items():
                if 'error' in data:
                    row = [contact, 'No', '', '', '', '', '', '', '', '', data['error']]
                else:
                    row = [
                        contact,
                        'Yes',
                        data.get('id', ''),
                        data.get('username', ''),
                        data.get('first_name', ''),
                        data.get('last_name', ''),
                        'Yes' if data.get('premium') else 'No',
                        'Yes' if data.get('verified') else 'No',
                        'Yes' if data.get('bot') else 'No',
                        data.get('last_seen', ''),
                        data.get('bio', '')[:100]  # Обрезаем длинный bio
                    ]
                writer.writerow(row)
        
        rprint(f"💾 Результаты сохранены:")
        rprint(f"   JSON: {json_file}")
        rprint(f"   CSV: {csv_file}")
    
    def show_summary(self, results: Dict[str, Any]):
        """Показывает сводку результатов"""
        total = results['total_contacts']
        processed = results['total_processed']
        errors = results['errors']
        found = processed - errors
        success_rate = results['success_rate']
        
        table = Table(title="📊 Сводка результатов")
        table.add_column("Метрика", style="cyan")
        table.add_column("Значение", style="green")
        
        table.add_row("Всего контактов", str(total))
        table.add_row("Обработано", str(processed))
        table.add_row("Найдено", str(found))
        table.add_row("Ошибок", str(errors))
        table.add_row("Успешность", f"{success_rate:.1f}%")
        
        console.print(table)
        
        # Статистика по найденным аккаунтам
        if found > 0:
            premium_count = sum(1 for r in results['results'].values() 
                              if 'premium' in r and r['premium'])
            verified_count = sum(1 for r in results['results'].values() 
                               if 'verified' in r and r['verified'])
            bot_count = sum(1 for r in results['results'].values() 
                          if 'bot' in r and r['bot'])
            
            rprint(f"\n📈 Дополнительная статистика:")
            rprint(f"   Premium аккаунты: {premium_count}")
            rprint(f"   Верифицированные: {verified_count}")
            rprint(f"   Боты: {bot_count}")

def main():
    rprint(Panel.fit("🚀 Массовая проверка Telegram контактов", style="bold green"))
    
    checker = BulkChecker()
    
    # Получаем файл с контактами
    while True:
        file_path = input("📁 Введите путь к файлу с контактами: ").strip()
        if not file_path:
            rprint("❌ Путь к файлу обязателен")
            continue
        
        try:
            contacts = checker.load_contacts_from_file(file_path)
            break
        except Exception as e:
            rprint(f"❌ Ошибка загрузки файла: {e}")
            continue
    
    # Настройки обработки
    batch_size = int(input("📦 Размер батча (по умолчанию 10): ") or "10")
    save_progress = input("💾 Сохранять прогресс? (y/n, по умолчанию y): ").lower() != 'n'
    
    rprint(f"\n🎯 Начинаем обработку {len(contacts)} контактов...")
    rprint(f"   Размер батча: {batch_size}")
    rprint(f"   Сохранение прогресса: {'Да' if save_progress else 'Нет'}")
    
    if input("\nПродолжить? (y/n): ").lower() != 'y':
        rprint("❌ Отменено")
        return
    
    try:
        # Обрабатываем контакты
        results = checker.process_contacts(contacts, batch_size, save_progress)
        
        # Показываем сводку
        checker.show_summary(results)
        
        # Сохраняем результаты
        checker.save_results(results)
        
        rprint("\n✅ Обработка завершена!")
        
    except Exception as e:
        rprint(f"\n❌ Ошибка обработки: {e}")

if __name__ == "__main__":
    main() 