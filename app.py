import alpaca_trade_api as tradeapi
import spotipy
import random
import time
from spotipy.oauth2 import SpotifyOAuth
import os 
from dotenv import load_dotenv # Load environment variables from .env file
load_dotenv()

# Spotify Credentials
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")  
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI") 
# Alpaca Credentials
ALPACA_API_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_API_SECRET = os.getenv("APCA_API_SECRET_KEY")
ALPACA_BASE_URL = os.getenv("APCA_API_BASE_URL")

SCOPE = 'playlist-modify-private playlist-modify-public user-read-private user-read-email'

def get_spotify_token():
    sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=REDIRECT_URI,  scope=SCOPE)
    token_info = sp_oauth.get_access_token(as_dict=True)
    if not token_info or 'access_token' not in token_info:
        print("Error: Unable to get access token")
        return None
    return token_info

# Initialize Alpaca API
alpaca = tradeapi.REST(ALPACA_API_KEY, ALPACA_API_SECRET, ALPACA_BASE_URL, api_version='v2')

# Define genres
genres = ['Pop', 'Rock', 'Hip-hop', 'Jazz', 'Classical', 'Electronic', 
          'Country', 'Rap', 'Latin', 'Indie', 'R&B', 'K-pop', 'Metal', 
          'Punk', 'Alternative', 'Fall', 'Chill']

def get_random_track(sp):
#gets a random genre
    random_genre = random.choice(genres)
    results = sp.search(q=f'genre:{random_genre}', type='track', limit=10)
    if results['tracks']['items']:
        track = random.choice(results['tracks']['items'])
        print(f"Selected Track: {track['name']} by {track['artists'][0]['name']} in genre {random_genre}")
        return track
    return None

def trade_stock(symbol, qty, action):
#writes out what will print for buy or sell
    try:
        # Check current position
        positions = alpaca.list_positions()
        current_position = next((pos for pos in positions if pos.symbol == symbol), None)

        print(f"Current position for {symbol}: {current_position}")  # Log current position

        if action == 'buy':
            if current_position is None:
                order = alpaca.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side='buy',
                    type='market',
                    time_in_force='gtc'
                )
                print(f"Buy Order Submitted: {order.id} - Status: {order.status}")
            else:
                print(f"Already holding position for {symbol}. No buy action taken.")
        elif action == 'sell':
            if current_position is not None:
                order = alpaca.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side='sell',
                    type='market',
                    time_in_force='gtc'
                )
                print(f"Sell Order Submitted: {order.id} - Status: {order.status}")
            else:
                print(f"No position to sell for {symbol}. No sell action taken.")
        else:
            print(f"No valid action '{action}' for {symbol}.")
    except Exception as e:
        print(f"Error executing order: {e}")


def generate_playlist_based_on_stocks(sp, stocks):
#creates the playlist based on the stocks
    mood = (
        "happy" if any(stock['price_change'] > 0 for stock in stocks) else
        "sad" if all(stock['price_change'] < 0 for stock in stocks) else
        "energetic" if any(stock['price_change'] > 1 for stock in stocks) else
        "relaxed" if all(stock['price_change'] == 0 for stock in stocks) else
        "nostalgic"
    )
    print(f"Determined mood for playlist creation based on AAPL: {mood}")

    genre_mapping = {
        "happy": ["Pop", "Dance", "Rock", "Electronic", "K-pop"],
        "sad": ["Chill", "Acoustic", "Classical", "Indie", "R&B"],
        "energetic": ["Hip-hop", "Punk", "Metal", "Alternative", "Rap"],
        "relaxed": ["Jazz", "Country", "Chill", "Fall", "Acoustic"],
        "nostalgic": ["Indie", "Alternative", "Classic Rock", "R&B", "Jazz"],
        "motivated": ["Electronic", "Rock", "Pop", "Hip-hop", "Metal"]
    }

    genre = random.choice(genre_mapping[mood])
    results = sp.search(q=f'genre:{genre}', type='track', limit=10)
    if results['tracks']['items']:
        track_uris = [track['uri'] for track in results['tracks']['items']]
        playlist = sp.user_playlist_create(user=sp.current_user()['id'], name=f'My Playlist based on {genre}', public=True)
        sp.user_playlist_add_tracks(user=sp.current_user()['id'], playlist_id=playlist['id'], tracks=track_uris)
        print(f"Playlist created with {genre} tracks based on stock performance.")
    else:
        print(f"No tracks found for genre '{genre}'.")
        print("Tracks selected for the playlist:")
    for track in results['tracks']['items']:
        print(f"- {track['name']} by {track['artists'][0]['name']}")


def is_market_open():
#checks if the market is open 
    clock = alpaca.get_clock()
    return clock.is_open

def main():
    #what starts the trade 
    token_info = get_spotify_token()
    if not token_info:
        return
    sp = spotipy.Spotify(auth=token_info['access_token']) 

#helps create the spotify playlist 
    stocks_data = [
        {'symbol': 'AAPL', 'price_change': 1.5} 
    ]

    try:
        while True:
            clock = alpaca.get_clock()
            current_time = clock.timestamp
            market_close_time = clock.next_close

            if not is_market_open():
                print("Market is closed. Waiting until market opens.")
                time.sleep(300)  
                continue  # Skip to the next iteration if market is closed

   # Check if it's within 20 minutes of market close and if it is then it closes anything by selling 
            if (market_close_time - current_time).total_seconds() <= 1200: 
                positions = alpaca.list_positions()
                for position in positions:
                    print(f"Selling position for {position.symbol} before market close.")
                    trade_stock(position.symbol, position.qty, 'sell')  
                print("All positions sold before market close.")
                break  

            track = get_random_track(sp)
            if track:
                positions = alpaca.list_positions()
                current_position = next((pos for pos in positions if pos.symbol == 'AAPL'), None)

                if current_position:
                    # If there is a current position, sell it
                    print(f"Determined action for AAPL: sell")
                    trade_stock('AAPL', 1, 'sell')  # Sell the stock
                else:
                    # If no current position, buy the stock
                    print(f"Determined action for AAPL: buy")
                    trade_stock('AAPL', 1, 'buy')  # Buy the stock

                generate_playlist_based_on_stocks(sp, stocks_data)
            time.sleep(240) 
    except Exception as e:
        print(f"An error occurred in the main loop: {e}")

if __name__ == "__main__":
    main()
