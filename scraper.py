import requests
from bs4 import BeautifulSoup, Tag
import re
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse
import time

class WikimediaEventsScraper:
    def __init__(self):
        self.base_url = "https://sw.wikipedia.org/wiki/Maalum:AllEvents"
        self.events_cache = None
        self.cache_timestamp = None
        self.cache_duration = 300  # 5 minutes
        
    def clear_cache(self):
        """Clear the events cache"""
        self.events_cache = None
        self.cache_timestamp = None
        
    def _is_cache_valid(self):
        """Check if cache is still valid"""
        if not self.cache_timestamp or not self.events_cache:
            return False
        return (time.time() - self.cache_timestamp) < self.cache_duration
    
    def _make_request(self, url):
        """Make HTTP request with proper headers"""
        headers = {
            'User-Agent': 'WikimediaEventsApp/1.0 (Educational Purpose)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'sw,en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"Error making request to {url}: {str(e)}")
            raise
    
    def _parse_date_range(self, date_text):
        """Parse date range from text"""
        try:
            if '–' in date_text:
                start_date, end_date = date_text.split('–', 1)
                return start_date.strip(), end_date.strip()
            else:
                return date_text.strip(), date_text.strip()
        except Exception as e:
            logging.warning(f"Error parsing date range '{date_text}': {str(e)}")
            return date_text, date_text
    
    def _extract_event_details(self, event_element):
        """Extract details from a single event element"""
        try:
            event_data = {}
            
            # Extract title and link
            title_link = event_element.find('a')
            if title_link:
                event_data['title'] = title_link.get_text(strip=True)
                event_data['link'] = urljoin(self.base_url, title_link.get('href', ''))
            else:
                event_data['title'] = 'Unknown Event'
                event_data['link'] = ''
            
            # Extract date range
            date_element = event_element.find('strong')
            if date_element:
                date_text = date_element.get_text(strip=True)
                start_date, end_date = self._parse_date_range(date_text)
                event_data['start_date'] = start_date
                event_data['end_date'] = end_date
                event_data['date_range'] = date_text
            
            # Extract participation options
            participation_element = event_element.find(text=re.compile(r'Participation options'))
            if participation_element:
                participation_parent = participation_element.find_parent()
                if participation_parent:
                    participation_text = participation_parent.find_next_sibling()
                    if participation_text:
                        event_data['participation_option'] = participation_text.get_text(strip=True)
            
            # Extract country
            country_element = event_element.find(text=re.compile(r'Country'))
            if country_element:
                country_parent = country_element.find_parent()
                if country_parent:
                    country_text = country_parent.find_next_sibling()
                    if country_text:
                        event_data['country'] = country_text.get_text(strip=True)
            
            # Extract event types
            event_types = []
            event_type_element = event_element.find(text=re.compile(r'Event types'))
            if event_type_element:
                event_type_parent = event_type_element.find_parent()
                if event_type_parent:
                    event_type_text = event_type_parent.find_next_sibling()
                    if event_type_text:
                        types_text = event_type_text.get_text(strip=True)
                        event_types = [t.strip() for t in types_text.split(',')]
            event_data['event_types'] = event_types
            
            # Extract wiki information
            wiki_element = event_element.find(text=re.compile(r'Wiki'))
            if wiki_element:
                wiki_parent = wiki_element.find_parent()
                if wiki_parent:
                    wiki_text = wiki_parent.find_next_sibling()
                    if wiki_text:
                        event_data['wiki'] = wiki_text.get_text(strip=True)
            
            # Extract topics/themes
            topics = []
            topics_element = event_element.find(text=re.compile(r'Mada'))  # "Mada" means "topics" in Swahili
            if topics_element:
                topics_parent = topics_element.find_parent()
                if topics_parent:
                    topics_text = topics_parent.find_next_sibling()
                    if topics_text:
                        topics_str = topics_text.get_text(strip=True)
                        topics = [t.strip() for t in topics_str.split(',')]
            event_data['topics'] = topics
            
            # Extract organizers
            organizers = []
            organizers_element = event_element.find(text=re.compile(r'Waandaaji'))  # "Waandaaji" means "organizers" in Swahili
            if organizers_element:
                organizers_parent = organizers_element.find_parent()
                if organizers_parent:
                    organizer_links = organizers_parent.find_next_sibling()
                    if organizer_links:
                        organizer_elements = organizer_links.find_all('a')
                        for org_element in organizer_elements:
                            organizers.append(org_element.get_text(strip=True))
            event_data['organizers'] = organizers
            
            # Generate a simple ID based on title
            event_data['id'] = hash(event_data['title']) & 0x7fffffff  # Ensure positive integer
            
            return event_data
            
        except Exception as e:
            logging.error(f"Error extracting event details: {str(e)}")
            return None
    
    def get_all_events(self):
        """Scrape all events from the Wikipedia page"""
        # Return cached data if valid
        if self._is_cache_valid():
            logging.info("Returning cached events data")
            return self.events_cache
        
        try:
            logging.info("Scraping events from Wikipedia...")
            response = self._make_request(self.base_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            events = []
            
            # Find the main events container
            # Looking for the list items that contain event information
            event_items = soup.find_all('li')
            
            for item in event_items:
                # Check if this item contains event information
                event_link = item.find('a', href=re.compile(r'/wiki/Event:'))
                if event_link:
                    event_data = self._extract_event_details(item)
                    if event_data and event_data.get('title') != 'Unknown Event':
                        events.append(event_data)
            
            # If we couldn't find events with the above method, try alternative parsing
            if not events:
                logging.warning("No events found with primary method, trying alternative parsing...")
                # Try to find events in a different structure
                content_div = soup.find('div', {'id': 'bodyContent'}) or soup.find('div', {'class': 'mw-body-content'})
                if content_div and isinstance(content_div, Tag):
                    links = content_div.find_all('a', href=re.compile(r'/wiki/Event:'))
                    for link in links:
                        if isinstance(link, Tag):
                            event_data = {
                                'id': hash(link.get_text(strip=True)) & 0x7fffffff,
                                'title': link.get_text(strip=True),
                                'link': urljoin(self.base_url, str(link.get('href', ''))),
                                'start_date': 'Unknown',
                                'end_date': 'Unknown',
                                'date_range': 'Unknown',
                                'participation_option': 'Unknown',
                                'country': 'Unknown',
                                'event_types': [],
                                'wiki': 'Unknown',
                                'topics': [],
                                'organizers': []
                            }
                            events.append(event_data)
            
            # Cache the results
            self.events_cache = events
            self.cache_timestamp = time.time()
            
            logging.info(f"Successfully scraped {len(events)} events")
            return events
            
        except Exception as e:
            logging.error(f"Error scraping events: {str(e)}")
            raise Exception(f"Failed to scrape events from Wikipedia: {str(e)}")
    
    def get_event_by_id(self, event_id):
        """Get a specific event by ID"""
        try:
            events = self.get_all_events()
            return next((event for event in events if event['id'] == event_id), None) if events else None
        except Exception as e:
            logging.error(f"Error getting event by ID {event_id}: {str(e)}")
            return None
