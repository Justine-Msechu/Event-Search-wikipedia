import os
import logging
from flask import Flask, render_template, request, jsonify, flash
from scraper import WikimediaEventsScraper

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your-secret-key-here")

# Initialize the scraper
scraper = WikimediaEventsScraper()

@app.route('/')
def index():
    """Main page displaying all events"""
    try:
        events = scraper.get_all_events()
        
        # Get unique values for filters
        countries = sorted(set(event.get('country', 'Unknown') for event in events if event.get('country') and event.get('country') != 'Unknown')) if events else []
        event_types = sorted(set(event_type for event in events for event_type in event.get('event_types', []))) if events else []
        participation_options = sorted(set(event.get('participation_option', 'Unknown') for event in events if event.get('participation_option') and event.get('participation_option') != 'Unknown')) if events else []
        
        return render_template('index_simple.html', 
                             events=events,
                             countries=countries,
                             event_types=event_types,
                             participation_options=participation_options,
                             total_events=len(events) if events else 0)
    except Exception as e:
        logging.error(f"Error loading events: {str(e)}")
        flash(f"Error loading events: {str(e)}", 'error')
        return render_template('index_simple.html', 
                             events=[],
                             countries=[],
                             event_types=[],
                             participation_options=[],
                             total_events=0)

@app.route('/refresh')
def refresh_events():
    """Refresh events data from Wikipedia"""
    try:
        scraper.clear_cache()
        events = scraper.get_all_events()
        flash(f"Successfully refreshed {len(events) if events else 0} events", 'success')
    except Exception as e:
        logging.error(f"Error refreshing events: {str(e)}")
        flash(f"Error refreshing events: {str(e)}", 'error')
    
    return index()

@app.route('/api/events')
def api_events():
    """API endpoint to get filtered events"""
    try:
        events = scraper.get_all_events()
        
        # Apply filters
        country = request.args.get('country')
        event_type = request.args.get('event_type')
        participation = request.args.get('participation')
        search = request.args.get('search', '').lower()
        
        filtered_events = events if events else []
        
        if country and country != 'all' and filtered_events:
            filtered_events = [e for e in filtered_events if e.get('country') == country]
        
        if event_type and event_type != 'all' and filtered_events:
            filtered_events = [e for e in filtered_events if event_type in e.get('event_types', [])]
        
        if participation and participation != 'all' and filtered_events:
            # Handle participation filtering with more intelligent matching
            if participation == 'online':
                filtered_events = [e for e in filtered_events if 'mtandaoni' in e.get('participation_option', '').lower()]
            elif participation == 'in_person':
                filtered_events = [e for e in filtered_events if 'ana kwa ana' in e.get('participation_option', '').lower() and 'mtandaoni' not in e.get('participation_option', '').lower()]
            elif participation == 'hybrid':
                filtered_events = [e for e in filtered_events if 'mtandaoni' in e.get('participation_option', '').lower() and 'ana kwa ana' in e.get('participation_option', '').lower()]
            else:
                filtered_events = [e for e in filtered_events if e.get('participation_option') == participation]
        
        if search and filtered_events:
            filtered_events = [e for e in filtered_events if 
                             search in e.get('title', '').lower() or
                             search in e.get('description', '').lower() or
                             search in ' '.join(e.get('topics', [])).lower()]
        
        return jsonify({
            'events': filtered_events,
            'total': len(filtered_events) if filtered_events else 0
        })
    except Exception as e:
        logging.error(f"Error in API events: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)