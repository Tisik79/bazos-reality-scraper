import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import anthropic
import os
from dotenv import load_dotenv
import logging
import pytz

# Nastavení loggeru
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class BazosRealityScraper:
    def __init__(self):
        load_dotenv()
        self.claude = anthropic.Client(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.locations = ['ostrava', 'karvina']
        self.base_url = 'https://reality.bazos.cz'
        self.csv_path = 'data/listings.csv'
        
    def get_time_from_text(self, time_text):
        """Převede textový čas z Bazoše na datetime objekt."""
        try:
            now = datetime.now(pytz.timezone('Europe/Prague'))
            if 'včera' in time_text:
                date = now.date() - timedelta(days=1)
                time = datetime.strptime(time_text.split()[1], '%H:%M').time()
                return datetime.combine(date, time)
            elif ':' in time_text:
                time = datetime.strptime(time_text, '%H:%M').time()
                return datetime.combine(now.date(), time)
            else:
                return datetime.strptime(time_text, '%d.%m.%Y')
        except Exception as e:
            logging.error(f"Chyba při parsování času: {e}")
            return None

    def is_recent_enough(self, time_text):
        """Kontroluje, zda je inzerát z posledních 2 hodin."""
        listing_time = self.get_time_from_text(time_text)
        if not listing_time:
            return False
        now = datetime.now(pytz.timezone('Europe/Prague'))
        return now - listing_time <= timedelta(hours=2)

    def get_recent_listings(self):
        """Získá inzeráty z posledních 2 hodin."""
        listings = []
        for location in self.locations:
            try:
                url = f"{self.base_url}/{location}/"
                response = requests.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                for inzerat in soup.find_all('div', class_='inzeraty'):
                    time_element = inzerat.find('span', class_='velikost10')
                    if not time_element:
                        continue
                        
                    time_text = time_element.text.strip()
                    if not self.is_recent_enough(time_text):
                        continue
                    
                    title = inzerat.find('h2', class_='nadpis').text.strip()
                    price = inzerat.find('div', class_='cena').text.strip()
                    id_element = inzerat.find('a')['href']
                    listing_id = id_element.split('/')[-2] if '/' in id_element else None
                    
                    listings.append({
                        'title': title,
                        'id': listing_id,
                        'location': location,
                        'price': price,
                        'time': time_text
                    })
                    
            except Exception as e:
                logging.error(f"Chyba při scrapování lokality {location}: {e}")
                
        return listings

    def save_to_csv(self, listings):
        """Uloží inzeráty do CSV souboru."""
        try:
            df = pd.DataFrame(listings)
            
            # Vytvoření adresáře, pokud neexistuje
            os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
            
            # Kontrola existence souboru
            if os.path.exists(self.csv_path):
                existing_df = pd.read_csv(self.csv_path)
                # Přidání pouze nových inzerátů
                df = pd.concat([existing_df, df]).drop_duplicates(subset=['id'])
            
            df.to_csv(self.csv_path, index=False)
            logging.info(f"Úspěšně uloženo {len(df)} inzerátů do {self.csv_path}")
            
        except Exception as e:
            logging.error(f"Chyba při ukládání do CSV: {e}")

    def run(self):
        """Hlavní metoda pro spuštění scraperu."""
        logging.info("Spouštím scraping...")
        listings = self.get_recent_listings()
        if listings:
            self.save_to_csv(listings)
            logging.info(f"Nalezeno {len(listings)} nových inzerátů")
        else:
            logging.info("Žádné nové inzeráty nenalezeny")

if __name__ == "__main__":
    scraper = BazosRealityScraper()
    scraper.run()
