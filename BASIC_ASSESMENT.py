import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import dotenv
from web3 import Web3
import requests
from dateutil import parser
import json
import pickle  # For saving/loading search history
from supabase import create_client, Client
from typing import List, Dict, Any
import random
from st_social_media_links import SocialMediaIcons

# Cookie management functions
def get_cookie(name: str, default: Any = None) -> Any:
    """Get a cookie value by name."""
    if name in st.session_state:
        return st.session_state[name]
    return default

def set_cookie(name: str, value: Any, max_age: int = 30 * 24 * 60 * 60) -> None:
    """Set a cookie value with optional max age in seconds (default 30 days)."""
    st.session_state[name] = value

def delete_cookie(name: str) -> None:
    """Delete a cookie by name."""
    if name in st.session_state:
        del st.session_state[name]

# Page configuration
st.set_page_config(
    page_title="Fraud Assessment Tool",
    page_icon="🔍",
    layout="wide"
)
# Custom CSS for page title color
st.markdown("""
    <style>
    .st-emotion-cache-10trbll {
        color: #102E50 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Social Media (main page only)
social_media_links = [
    "https://www.linkedin.com/in/oscarquirogap/",
    "mailto:contact@onanalytics.co",  # Changed email
]
social_media_icons = SocialMediaIcons(social_media_links)

# Assigning variables
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        client = create_client(url, key)
        print("Supabase client created successfully")
        return client
    except Exception as e:
        st.error(f"Failed to create Supabase client: {str(e)}")
        print(f"Failed to create Supabase client: {str(e)}")
        return None

supabase = init_connection()

# Set up file paths
try:    
    # File path configuration
    file_path = "C:\\Users\\Oscar\\CascadeProjects\\assesments"
    os.chdir(file_path)

    # Search history file path
    search_history_path = os.path.join(file_path, "search_history.pkl")

except Exception as e:
    print(f"Error setting up file paths: {str(e)}")
    search_history_path = None

# Load suspicious tokens by blockchain
def load_suspicious_tokens_by_blockchain(blockchain):
    try:
        # First check if supabase client is available
        if supabase is None:
            st.error("Supabase client is not initialized. Check your credentials.")
            return pd.DataFrame()

        all_data = []
        page_size = 1000
        current_page = 0
        print(f"Loading suspicious tokens for blockchain: {blockchain}")  # Debug print
        while True:
            response = supabase.table("suspicious_tokens_directory") \
                .select("*") \
                .eq("blockchain", blockchain.lower()) \
                .range(current_page * page_size, (current_page + 1) * page_size - 1) \
                .execute()
            if not hasattr(response, "data") or not response.data:
                break
            all_data.extend(response.data)
            if len(response.data) < page_size:
                break
            current_page += 1
        if all_data:
            df = pd.DataFrame(all_data)
            print(f"Found {len(df)} suspicious tokens for {blockchain}")  # Debug print
            print(f"Columns in suspicious tokens DataFrame: {df.columns.tolist()}")  # Debug print
            # Check if tag_1 column exists
            if 'tag_1' not in df.columns:
                print("WARNING: 'tag_1' column not found in suspicious tokens data")
                # Add a default tag_1 column if it doesn't exist
                df['tag_1'] = 'Unknown'
            # Check if tag column exists
            if 'tag' not in df.columns:
                print("WARNING: 'tag' column not found in suspicious tokens data")
                # Add a default tag column if it doesn't exist
                df['tag'] = 'Unknown'
            # Check if created_block_timestamp column exists (correct name)
            if 'created_block_timestamp' not in df.columns:
                print("WARNING: 'created_block_timestamp' column not found in suspicious tokens data")
                df['created_block_timestamp'] = ''
            # For backwards compatibility, remove any old created_blocktime_stamp column
            if 'created_blocktime_stamp' in df.columns:
                df = df.drop(columns=['created_blocktime_stamp'])
            # Check if name column exists
            if 'name' not in df.columns:
                print("WARNING: 'name' column not found in suspicious tokens data")
                df['name'] = ''
            # Remove duplicate tokens based on contract_address (keep first occurrence)
            df = df.drop_duplicates(subset=['contract_address'])
            return df[['contract_address', 'blockchain', 'tag', 'tag_1', 'created_block_timestamp', 'name']]
        print(f"No suspicious tokens found for {blockchain}")  # Debug print
        return pd.DataFrame()
    except Exception as e:
        print(f"Error loading suspicious tokens: {str(e)}")
        return pd.DataFrame()

def load_safe_tokens_by_blockchain(blockchain):
    try:
        # First check if supabase client is available
        if supabase is None:
            st.error("Supabase client is not initialized. Check your credentials.")
            return pd.DataFrame()
        
        all_data = []
        page_size = 1000
        current_page = 0
            
        print(f"Loading safe tokens for blockchain: {blockchain}")  # Debug print
            
        while True:
            response = supabase.table("safe_tokens") \
                .select("*") \
                .eq("blockchain", blockchain.lower()) \
                .range(current_page * page_size, (current_page + 1) * page_size - 1) \
                .execute()
                
            if not hasattr(response, "data") or not response.data:
                break
                
            all_data.extend(response.data)
                
            if len(response.data) < page_size:
                break
            
            current_page += 1
            
        if all_data:
            df = pd.DataFrame(all_data)
            print(f"Found {len(df)} safe tokens for {blockchain}")  # Debug print
            print(f"Columns in safe tokens DataFrame: {df.columns.tolist()}")  # Debug print
                
            # Check if tag_1 column exists
            if 'tag_1' not in df.columns:
                print("WARNING: 'tag_1' column not found in safe tokens data")
                # Add a default tag_1 column if it doesn't exist
                df['tag_1'] = 'No Detail'
                
            return df[['contract_address', 'blockchain', 'tag', 'tag_1']]
            
        print(f"No safe tokens found for {blockchain}")  # Debug print
        return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Error loading safe tokens for {blockchain}: {str(e)}")
        import traceback
        st.error(f"Detailed error: {traceback.format_exc()}")
        return pd.DataFrame()

# Modify the identify_suspicious_transfers function to use blockchain-specific data
def identify_suspicious_transfers(transfers_df):
    if not transfers_df.empty:
        try:
            # Get the blockchain from the transfers data
            blockchain = transfers_df['blockchain'].iloc[0]
                
            # Load suspicious tokens for this specific blockchain
            suspicious_tokens = load_suspicious_tokens_by_blockchain(blockchain)
                
            if not suspicious_tokens.empty:
                # Ensure lowercase contract addresses for consistent matching
                transfers_df['contract_address'] = transfers_df['contract_address'].str.lower()
                suspicious_tokens['contract_address'] = suspicious_tokens['contract_address'].str.lower()
                
                # Merge transfers with suspicious tokens directory
                suspicious_transfers = pd.merge(
                    transfers_df,
                    suspicious_tokens,
                    on=['contract_address'],
                    how='inner'
                )
                
                return suspicious_transfers
            else:
                print(f"No high risk tokens found for blockchain {blockchain}")
                return pd.DataFrame()
                
        except Exception as e:
            st.error(f"Error in identify_suspicious_transfers: {str(e)}")
            return pd.DataFrame()
        
    return pd.DataFrame()

def identify_safe_transfers(transfers_df):
    if not transfers_df.empty:
        try:
            # Get the blockchain from the transfers data
            blockchain = transfers_df['blockchain'].iloc[0]
                
            # Load safe tokens for this specific blockchain
            safe_tokens = load_safe_tokens_by_blockchain(blockchain)
                
            if not safe_tokens.empty:
                # Ensure lowercase contract addresses for consistent matching
                transfers_df['contract_address'] = transfers_df['contract_address'].str.lower()
                safe_tokens['contract_address'] = safe_tokens['contract_address'].str.lower()
                
                # Merge transfers with safe tokens directory
                safe_transfers = pd.merge(
                    transfers_df,
                    safe_tokens,
                    on=['contract_address'],
                    how='inner'
                )
                
                return safe_transfers
            else:
                print(f"No safe tokens found for blockchain {blockchain}")
                return pd.DataFrame()
                
        except Exception as e:
            st.error(f"Error in identify_safe_transfers: {str(e)}")
            return pd.DataFrame()
        
    return pd.DataFrame()

try:
    suspicious_tokens_loaded = True
except Exception as e:
    suspicious_tokens_loaded = False
    search_history_path = None

# Load search history or create a new one
def load_search_history() -> List[Dict[str, Any]]:
    """Load search history from cookies."""
    history = get_cookie('search_history', [])
    return history

# Save search history
def save_search_history(history: List[Dict[str, Any]]) -> bool:
    """Save search history to cookies."""
    try:
        set_cookie('search_history', history)
        return True
    except Exception as e:
        st.warning(f"Could not save search history: {str(e)}")
        return False

# Function to add a search to history
def add_to_search_history(address: str, blockchain: str) -> None:
    """Add a new search to history using cookies."""
    # Create a new entry with timestamp
    new_entry = {
        'timestamp': datetime.now().isoformat(),  # Convert to string for JSON serialization
        'address': address,
        'blockchain': blockchain
    }
    
    # Get current history from cookies
    history = load_search_history()
    
    # Check if this address+blockchain combo already exists
    existing_entries = [
        i for i, entry in enumerate(history)
        if entry['address'].lower() == address.lower() and entry['blockchain'] == blockchain
    ]
    
    # If it exists, remove the old entry
    if existing_entries:
        history.pop(existing_entries[0])
    
    # Add the new entry at the beginning of the list
    history.insert(0, new_entry)
    
    # Limit history to last 100 searches
    if len(history) > 100:
        history = history[:100]
    
    # Save updated history to cookies
    save_search_history(history)




# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #102E50 !important;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .sub-header {
        font-size: 2.0rem;
        color: #424242;
        margin-bottom: 1rem;
    }
    .block-container {
        padding: 2rem 1rem;
    }
    .info-box {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #ffffff;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .warning-tag {
        background-color: #ffcdd2;
        color: #b71c1c;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .history-item {
        padding: 8px;
        margin: 4px 0;
        border-radius: 4px;
        background-color: #f5f5f5;
        cursor: pointer;
    }
    .history-item:hover {
        background-color: #e0e0e0;
    }
    .history-timestamp {
        color: #757575;
        font-size: 0.8rem;
    }
    .history-address {
        font-weight: bold;
    }
    .history-blockchain {
        color: #1E88E5;
        font-size: 0.9rem;
    }
    .search-container {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    .search-title {
        color: #1E3A8A;
        font-size: 1.2rem;
        margin-bottom: 1rem;
    }
    .dataframe-container {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    .page-selector {
        width: 100px;
        float: right;
    }
    </style>
""", unsafe_allow_html=True)




# Application title and description
st.markdown("<h1 class='main-header'>Fraud Assessment Tool</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; margin-bottom: 2rem;'>Try Once - Run a Fraud Diagnostic on any Address</p>", unsafe_allow_html=True)


# Create columns for the main controls and search history
left_col, right_col = st.columns([3, 1])


with left_col:
    # Input form container
    with st.container():
        st.markdown("<div class='search-container'>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            address = st.text_input("💼 Address", placeholder="Enter blockchain address (0x...)")
        with col2:
            blockchain_options = {
                "ethereum": "Ethereum (ETH) ⟠",
                "bsc": "BNB Chain 🔶",
                "polygon": "Polygon (MATIC) 🟣",
                "arbitrum": "Arbitrum (ARBI) 🔵",
                "optimism": "Optimism (OP) 🔴",
                "base": "Base (BASE) 🟢",
                "blast": "Blast (BLAST) 💥"
            }
            blockchain = st.selectbox(
                "🔗 Network",
                options=list(blockchain_options.keys()),
                format_func=lambda x: blockchain_options[x]
            )
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)  # Spacing for alignment
            search_button = st.button("🔍 Analyze", use_container_width=True)
            try_example_button = st.button("🎲 Try Example", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)



with right_col:
    pass




# Function to get token transfers data using your updated SQL query
def get_token_transfers(address_searched: str, blockchain: str) -> pd.DataFrame:
    """Fetch the last 100 ERC-20 token transfers for an address using Alchemy's enhanced API."""
    try:
        dotenv.load_dotenv(".env")
        ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
        # Map blockchain to Alchemy URL
        blockchain = blockchain.lower()
        if blockchain == "ethereum":
            ALCHEMY_URL = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
        elif blockchain == "polygon":
            ALCHEMY_URL = f"https://polygon-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
        elif blockchain == "arbitrum":
            ALCHEMY_URL = f"https://arb-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
        elif blockchain == "optimism":
            ALCHEMY_URL = f"https://opt-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
        elif blockchain == "blast":
            ALCHEMY_URL = f"https://blast-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
        elif blockchain == "base":
            ALCHEMY_URL = f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
        elif blockchain in ["bsc", "binance", "binance smart chain", "binance-smart-chain"]:
            ALCHEMY_URL = f"https://bnb-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
        else:
            st.warning(f"Blockchain '{blockchain}' not recognized. Defaulting to Ethereum mainnet.")
            ALCHEMY_URL = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
            blockchain = "ethereum"
        web3 = Web3(Web3.HTTPProvider(ALCHEMY_URL))
        if not web3.is_connected():
            st.error(f"Connection to {blockchain.title()} blockchain failed!")
            return pd.DataFrame()
        else:
            print(f"Connected to {blockchain.title()} blockchain")

        ADDRESS = address_searched
        seven_days_ago = int((datetime.now() - timedelta(days=7)).timestamp())
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "alchemy_getAssetTransfers",
            "params": [
                {
                    "fromBlock": "0x0",
                    "toBlock": "latest",
                    "maxCount": "0x64",
                    "excludeZeroValue": False,
                    "category": ["erc20"],
                    "fromAddress": ADDRESS,
                    "withMetadata": True,
                    "order": "desc"
                }
            ]
        }
        print(f"Fetching outgoing ERC-20 transfers for {ADDRESS} on {blockchain.title()}...")
        response = requests.post(ALCHEMY_URL, json=payload)
        outgoing_transfers = []
        if response.status_code == 200:
            data = response.json()
            if "result" in data and "transfers" in data["result"]:
                outgoing_transfers = data["result"]["transfers"]

        else:
            print(f"Error fetching outgoing transfers: {response.status_code} {response.text}")

        # Now fetch incoming transfers
        payload["params"][0].pop("fromAddress", None)
        payload["params"][0]["toAddress"] = ADDRESS
        print(f"Fetching incoming ERC-20 transfers for {ADDRESS} on {blockchain.title()}...")
        response = requests.post(ALCHEMY_URL, json=payload)
        incoming_transfers = []
        if response.status_code == 200:
            data = response.json()
            if "result" in data and "transfers" in data["result"]:
                incoming_transfers = data["result"]["transfers"]

        else:
            print(f"Error fetching incoming transfers: {response.status_code} {response.text}")

        # Combine and process all transfers
        all_transfers = outgoing_transfers + incoming_transfers
        all_transfers.sort(key=lambda x: int(x.get("blockNum", "0x0"), 16), reverse=True)
        processed_transfers = []
        for tx in all_transfers:
            block_timestamp_str = tx.get("metadata", {}).get("blockTimestamp", "")
            if not block_timestamp_str:
                continue
            block_datetime = parser.isoparse(block_timestamp_str)
            block_timestamp = int(block_datetime.timestamp())
            if block_timestamp >= seven_days_ago:
                processed_transfers.append({
                    "block_number": int(tx.get("blockNum", "0x0"), 16),
                    "timestamp": block_timestamp,
                    "tx_hash": tx.get("hash", ""),
                    "contract_address": tx.get("rawContract", {}).get("address", ""),
                    "symbol": tx.get("asset", ""),
                    "from_address": tx.get("from", ""),
                    "to_address": tx.get("to", ""),
                    "amount": float(tx.get("value", 0)),
                    "block_timestamp": block_datetime.strftime('%Y-%m-%d %H:%M:%S')
                })
                if len(processed_transfers) >= 100:
                    break
        # Add blockchain column
        for tx in processed_transfers:
            tx["blockchain"] = blockchain

        transfers_df = pd.DataFrame(processed_transfers)
        # DEBUG: Print a sample of from_address and to_address values
        print("Sample from_address and to_address values:")
        print(transfers_df[["from_address", "to_address"]].head(10))
        return transfers_df
    except Exception as e:
        st.error(f"Error fetching token transfers: {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame on error


# Function to analyze token transfers data including suspicious activity
def analyze_transfers_data(transfers_df):
    if transfers_df.empty:
        return None
   
    try:
        # Identify suspicious transfers
        suspicious_transfers = identify_suspicious_transfers(transfers_df)
        suspicious_count = len(suspicious_transfers) if not suspicious_transfers.empty else 0 #number of suspicious transfers

        # Identify safe transfers
        safe_transfers = identify_safe_transfers(transfers_df)
        safe_count = len(safe_transfers) if not safe_transfers.empty else 0 #number of safe transfers
   
        # --- Compute activity timeline for all and suspicious transfers ---
        transfers_df['date'] = pd.to_datetime(transfers_df['block_timestamp']).dt.date
        all_counts = transfers_df.groupby('date').size().reset_index(name='All Transfers')
        if not suspicious_transfers.empty:
            suspicious_transfers['date'] = pd.to_datetime(suspicious_transfers['block_timestamp']).dt.date
            suspicious_counts = suspicious_transfers.groupby('date').size().reset_index(name='Suspicious Transfers')
        else:
            suspicious_counts = pd.DataFrame(columns=['date', 'Suspicious Transfers'])
        activity_timeline = pd.merge(all_counts, suspicious_counts, on='date', how='left').fillna(0)
        activity_timeline = activity_timeline.set_index('date').sort_index()

        # --- Compute unique tokens timeline for all and suspicious transfers ---
        tokens_all = transfers_df.groupby('date')['contract_address'].nunique().reset_index(name='All Tokens')
        if not suspicious_transfers.empty:
            tokens_suspicious = suspicious_transfers.groupby('date')['contract_address'].nunique().reset_index(name='Suspicious Tokens')
        else:
            tokens_suspicious = pd.DataFrame(columns=['date', 'Suspicious Tokens'])
        tokens_timeline = pd.merge(tokens_all, tokens_suspicious, on='date', how='left').fillna(0)
        tokens_timeline = tokens_timeline.set_index('date').sort_index()

        # Get total number of transfers
        total_transfers = len(transfers_df) #total number of transfers in protocol for the last seven days
   

        # Get unique tokens
        unique_tokens = transfers_df['contract_address'].nunique()
   
        # Get top tokens by transfer count
        top_tokens = transfers_df['contract_address'].value_counts().head(5).to_dict()
   
        # Get first and last activity dates
        first_activity = transfers_df['block_timestamp'].min() #This is the first transfers identified
        last_activity = transfers_df['block_timestamp'].max() #This is the last transfers identified
   
        # Get recent transfers (include suspicious and safe tags if applicable)
        recent_transfers = transfers_df.sort_values('block_timestamp', ascending=False)
        recent_transfers_list = []
   
        for _, row in recent_transfers.iterrows():
            # Check if this transfer is in suspicious_transfers
            is_suspicious = False
            is_safe = False
            tag = None
            tag_1 = None
       
            if not suspicious_transfers.empty:
                suspicious_match = suspicious_transfers[
                    (suspicious_transfers['tx_hash'] == row['tx_hash']) &
                    (suspicious_transfers['contract_address'] == row['contract_address'])
                ]
                if not suspicious_match.empty:
                    is_suspicious = True
                    tag = suspicious_match.iloc[0]['tag']
                    # Safely get tag_1 if it exists
                    if 'tag_1' in suspicious_match.columns:
                        tag_1 = suspicious_match.iloc[0]['tag_1']
            
            # Check if this transfer is in safe_transfers
            if not safe_transfers.empty and not is_suspicious:
                safe_match = safe_transfers[
                    (safe_transfers['tx_hash'] == row['tx_hash']) &
                    (safe_transfers['contract_address'] == row['contract_address'])
                ]
                if not safe_match.empty:
                    is_safe = True
                    tag = safe_match.iloc[0]['tag']
                    # Safely get tag_1 if it exists
                    if 'tag_1' in safe_match.columns:
                        tag_1 = safe_match.iloc[0]['tag_1']
           
            recent_transfers_list.append({
                "tx_hash": str(row['tx_hash']),  # Full, no shortening
                "contract_address": str(row['contract_address']),  # Full, no shortening
                "from_address": row.get('from_address', ''),
                "to_address": row.get('to_address', ''),
                "symbol": row['symbol'] if pd.notna(row['symbol']) else "Unknown",
                # Robustly handle both string and datetime for block_timestamp
                "block_timestamp": row['block_timestamp'],
                "time": parser.parse(row['block_timestamp']).strftime('%Y-%m-%d %H:%M:%S') if isinstance(row['block_timestamp'], str) else row['block_timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                "suspicious": is_suspicious,
                "safe": is_safe,
                "tag": tag if tag else "Caution",
                "tag_1": tag_1 if tag_1 else "No Detail"
            })
       
        # Calculate suspicious token metrics
        if not suspicious_transfers.empty:
            suspicious_tokens = suspicious_transfers['contract_address'].nunique()  # Number of unique suspicious tokens
            
            # Debug print to check columns
            print("Suspicious transfers columns:", suspicious_transfers.columns.tolist())
            
            # Calculate suspicious_tags dynamically
            suspicious_tags = (
                suspicious_transfers
                .groupby('tag_1')['contract_address']
                .nunique()
                .reset_index()
                .rename(columns={'contract_address': 'count', 'tag_1': 'tag'})
            )
            total_suspicious_tokens = suspicious_transfers['contract_address'].nunique()
            suspicious_tags['percent'] = (suspicious_tags['count'] / total_suspicious_tokens * 100).round(1) if total_suspicious_tokens else 0
        else:
            suspicious_tokens = 0
            suspicious_tags = pd.DataFrame(columns=['tag', 'count', 'percent'])

        # Calculate safe token metrics
        if not safe_transfers.empty:
            safe_tokens = safe_transfers['contract_address'].nunique()  # Number of unique safe tokens
            
            # Debug print to check columns
            print("Safe transfers columns:", safe_transfers.columns.tolist())
            
            # Safely handle tag_1 grouping
            if 'tag_1' in safe_transfers.columns:
                safe_tags = safe_transfers.groupby('tag_1')['contract_address'].nunique().reset_index()
                safe_tags.columns = ['tag', 'count']
                # For stacked bar: get percentage per tag
                safe_tags['percent'] = safe_tags['count'] / safe_tokens * 100
            else:
                # If tag_1 doesn't exist, create a default DataFrame
                safe_tags = pd.DataFrame({
                    'tag': ['Unknown'],
                    'count': [safe_tokens],
                    'percent': [100.0]
                })
        else:
            safe_tokens = 0
            safe_tags = pd.DataFrame(columns=['tag', 'count', 'percent'])
   
        return {
            "summary": {
                "total_transfers": total_transfers,
                "unique_tokens": unique_tokens,
                "suspicious_count": suspicious_count,
                "suspicious_tokens": suspicious_tokens,
                "suspicious_senders": len(suspicious_transfers["from_address"].unique()) if not suspicious_transfers.empty else 0,
                "safe_count": safe_count,
                "safe_tokens": safe_tokens,
                "safe_senders": len(safe_transfers["from_address"].unique()) if not safe_transfers.empty else 0,
            },
            "top_tokens": top_tokens,
            "activity_timeline": activity_timeline,
            "tokens_timeline": tokens_timeline,
            "recent_transfers": recent_transfers_list,
            "suspicious_transfers": suspicious_transfers,
            "suspicious_tags": suspicious_tags,
            "safe_transfers": safe_transfers,
            "safe_tags": safe_tags,
            "raw_data": transfers_df
        }
    except Exception as e:
        st.error(f"Error analyzing transfers data: {str(e)}")
        # Add more detailed error information
        import traceback
        st.error(f"Detailed error: {traceback.format_exc()}")
        return None




# Show mock data for development/testing
def get_mock_data():
    # Each contract_address has only one tag_1 (fraud type)
    mock_suspicious_transfers = pd.DataFrame({
        "tx_hash": [
            # ETH token (Phishing)
            "0x1234...a1", "0x1234...a2", "0x1234...a3",
            # SCAM token (Fake Native)
            "0x7890...b1", "0x7890...b2",
            # FAKE token (Fake Stablecoin)
            "0x3456...c1", "0x3456...c2",
            # BUSD token (Fake Native)
            "0x2222...d1",
            # MATIC token (Phishing)
            "0x3333...e1", "0x3333...e2",
            # ARBSCAM token (Fake Stablecoin)
            "0x4444...f1"
        ],
        "name": [
            # ETH
            "Ether", "Ether", "Ether",
            # SCAM
            "Scam Token", "Scam Token",
            # FAKE
            "Fake USD", "Fake USD",
            # BUSD
            "Fake BUSD",
            # MATIC
            "Fake Matic", "Fake Matic",
            # ARBSCAM
            "ARB Scam"
        ],
        "block_timestamp": pd.to_datetime([
            # ETH
            "2023-11-28 14:25:16", "2023-11-27 10:15:30", "2023-11-26 08:45:22",
            # SCAM
            "2023-11-28 13:00:00", "2023-11-27 11:00:00",
            # FAKE
            "2023-11-28 12:00:00", "2023-11-27 12:00:00",
            # BUSD
            "2023-11-25 15:00:00",
            # MATIC
            "2023-11-28 11:00:00", "2023-11-27 13:00:00",
            # ARBSCAM
            "2023-11-28 10:00:00"
        ]),
        "created_block_timestamp": [
            # Use the same values as block_timestamp for mock data
            "2023-11-28 14:25:16", "2023-11-27 10:15:30", "2023-11-26 08:45:22",
            "2023-11-28 13:00:00", "2023-11-27 11:00:00",
            "2023-11-28 12:00:00", "2023-11-27 12:00:00",
            "2023-11-25 15:00:00",
            "2023-11-28 11:00:00", "2023-11-27 13:00:00",
            "2023-11-28 10:00:00"
        ],
        "blockchain": ["ethereum"] * 11,
        "contract_address": [
            "0x1234...abcd", "0x1234...abcd", "0x1234...abcd",
            "0x7890...efgh", "0x7890...efgh",
            "0x3456...ijkl", "0x3456...ijkl",
            "0x2222...mnop",
            "0x3333...qrst", "0x3333...qrst",
            "0x4444...uvwx"
        ],
        "symbol": [
            "ETH", "ETH", "ETH",
            "SCAM", "SCAM",
            "FAKE", "FAKE",
            "BUSD",
            "MATIC", "MATIC",
            "ARBSCAM"
        ],
        "from_address": [
            "0xaaa...111", "0xaaa...222", "0xaaa...333",
            "0xbbb...111", "0xbbb...222",
            "0xccc...111", "0xccc...222",
            "0xddd...111",
            "0xeee...111", "0xeee...222",
            "0xfff...111"
        ],
        "tag": [
            "High Risk", "High Risk", "High Risk",
            "High Risk", "High Risk",
            "High Risk", "High Risk",
            "High Risk",
            "High Risk", "High Risk",
            "High Risk"
        ],
        "tag_1": [
            "Phishing", "Phishing", "Phishing",
            "Fake Native", "Fake Native",
            "Fake Stablecoin", "Fake Stablecoin",
            "Fake Native",
            "Phishing", "Phishing",
            "Fake Stablecoin"
        ]
    })

    # Create mock safe transfers
    mock_safe_transfers = pd.DataFrame({
        "tx_hash": ["0xaaa...111", "0xaaa...222", "0xaaa...333"],
        "block_timestamp": pd.to_datetime(["2023-11-27 10:15:30", "2023-11-26 08:45:22", "2023-11-25 16:30:45"]),
        "blockchain": ["ethereum", "ethereum", "ethereum"],
        "contract_address": ["0xc890...1234", "0xc456...7890", "0xc123...4567"],
        "symbol": ["USDC", "WETH", "ETH"],
        "from_address": ["0xaaa...111", "0xaaa...222", "0xaaa...333"],
        "tag": ["Safe", "Safe", "Safe"],
        "tag_1": ["No Detail", "No Detail", "No Detail"]
    })
   
    # Combine all mock transfers for total and unique calculations
    all_transfers = pd.concat([mock_suspicious_transfers, mock_safe_transfers], ignore_index=True)


    # Calculate summary metrics dynamically
    total_transfers = len(all_transfers)
    unique_tokens = all_transfers['contract_address'].nunique()
    suspicious_count = len(mock_suspicious_transfers)
    suspicious_tokens = mock_suspicious_transfers['contract_address'].nunique()
    suspicious_senders = mock_suspicious_transfers['from_address'].nunique()
    safe_count = len(mock_safe_transfers)
    safe_tokens = mock_safe_transfers['contract_address'].nunique()
    safe_senders = mock_safe_transfers['from_address'].nunique()

    # --- Compute activity timeline for all and suspicious transfers ---
    all_transfers['date'] = pd.to_datetime(all_transfers['block_timestamp']).dt.date
    suspicious_transfers = mock_suspicious_transfers.copy()
    suspicious_transfers['date'] = pd.to_datetime(suspicious_transfers['block_timestamp']).dt.date

    all_counts = all_transfers.groupby('date').size().reset_index(name='All Transfers')
    suspicious_counts = suspicious_transfers.groupby('date').size().reset_index(name='Suspicious Transfers')
    activity_timeline = pd.merge(all_counts, suspicious_counts, on='date', how='left').fillna(0)
    activity_timeline = activity_timeline.set_index('date').sort_index()

    # --- Compute unique tokens timeline for all and suspicious transfers ---
    tokens_all = all_transfers.groupby('date')['contract_address'].nunique().reset_index(name='All Tokens')
    tokens_suspicious = suspicious_transfers.groupby('date')['contract_address'].nunique().reset_index(name='Suspicious Tokens')
    tokens_timeline = pd.merge(tokens_all, tokens_suspicious, on='date', how='left').fillna(0)
    tokens_timeline = tokens_timeline.set_index('date').sort_index()

    # --- Compute suspicious tags (Tokens by Fraud Type) dynamically ---
    suspicious_tags = (
        mock_suspicious_transfers
        .groupby('tag_1')['contract_address']
        .nunique()
        .reset_index()
        .rename(columns={'contract_address': 'count', 'tag_1': 'tag'})
    )
    total_suspicious_tokens = suspicious_tokens
    suspicious_tags['percent'] = (suspicious_tags['count'] / total_suspicious_tokens * 100).round(1) if total_suspicious_tokens else 0

    return {
        "summary": {
            "total_transfers": total_transfers,
            "unique_tokens": unique_tokens,
            "suspicious_count": suspicious_count,
            "suspicious_tokens": suspicious_tokens,
            "suspicious_senders": suspicious_senders,
            "safe_count": safe_count,
            "safe_tokens": safe_tokens,
            "safe_senders": safe_senders,
        },
        "top_tokens": {
            "ETH": 45,
            "USDC": 32,
            "WETH": 28,
            "USDT": 19,
            "AAVE": 10
        },
        "activity_timeline": activity_timeline,
        "tokens_timeline": tokens_timeline,
        "recent_transfers": [
            (
                lambda tag, tx_hash, contract_address, time, from_address, to_address: {
                    "tx_hash": tx_hash,
                    "contract_address": contract_address,
                    "from_address": from_address,
                    "to_address": to_address,
                    "symbol": "ETH",
                    "block_timestamp": time,
                    "created_block_timestamp": (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d %H:%M:%S'),
                    "suspicious": tag == "High Risk",
                    "safe": tag == "Safe",
                    "tag": tag,
                    "tag_1": (
                        random.choice(["Phishing", "Fake Native", "Fake Stablecoin"]) if tag == "High Risk" else "No Detail"
                    )
                }
            )(
                # tag assignment logic
                ("High Risk" if i % 3 == 0 else ("Safe" if i % 3 == 1 else "Caution")),
                f"0x{i}234...abcd",
                f"0xc{i}23...4567",
                (datetime.now() - timedelta(hours=i)).strftime('%Y-%m-%d %H:%M:%S'),
                f"0xFrom{i:02d}...{i*7%100:02d}",
                f"0xTo{i:02d}...{i*13%100:02d}"
            )
            for i in range(20)  # Create 20 mock transfers for testing
        ],
        "suspicious_transfers": mock_suspicious_transfers,
        "suspicious_tags": suspicious_tags,
        "safe_transfers": mock_safe_transfers,
        "safe_tags": pd.DataFrame({
            "tag": ["Safe", "Safe", "Safe"],
            "count": [1, 1, 1],
            "percent": [33.3, 33.3, 33.3]
        }),
        "raw_data": pd.DataFrame({
            "tx_hash": ["0x1234...abcd", "0x5678...efgh", "0x9012...ijkl", "0x3456...mnop", "0x7890...qrst"],
            "block_timestamp": pd.date_range(start="2023-11-15", periods=5, freq="D"),
            "address": ["0xuser...1234", "0xuser...1234", "0xuser...1234", "0xuser...1234", "0xuser...1234"],
            "blockchain": ["ethereum", "ethereum", "ethereum", "ethereum", "ethereum"],
            "contract_address": ["0xc123...4567", "0xc890...1234", "0xc456...7890", "0xc123...4567", "0xc789...0123"],
            "symbol": ["ETH", "USDC", "WETH", "ETH", "SCAM"],
        })
    }


# Processing and results display
if search_button:
    # Reset results first (in case this is a new search while results are displayed)
    delete_cookie('has_searched')
    delete_cookie('current_results')
    
    if address and blockchain:
        # Add this search to history
        add_to_search_history(address, blockchain)
        
        # Set search state to True
        set_cookie('has_searched', True)
        
        # Get data from API
        try:
            # Get token transfers data from Flipside API
            with st.spinner('Analyzing blockchain activity...'):
                transfers_df = get_token_transfers(address, blockchain)
            
            # Check if any transfers were found
            if transfers_df.empty:
                st.warning(f"No transactions found for address {address} on {blockchain}. This could mean:\n" + 
                          "- The address has no transactions in the last 7 days\n" +
                          "- The address doesn't exist\n" +
                          "- The address might be on a different network")
                delete_cookie('has_searched')
                st.stop()
            
            # Analyze the transfers data
            data = analyze_transfers_data(transfers_df)
            if not data:
                st.error("Unable to analyze data. Please try again or check the address.")
                delete_cookie('has_searched')
                st.stop()
            
            # Store results in cookies
            set_cookie('current_results', data)
            
        except Exception as e:
            st.error(f"Error processing data: {str(e)}")
            st.stop()
    else:
        st.error("Please enter an address and select a blockchain.")

# Add this block after the above if block
if try_example_button:
    # Set cookie to indicate a search has occurred
    set_cookie('has_searched', True)
    # Store mock data as the current results
    set_cookie('current_results', get_mock_data())
    # Optionally, show a message
    st.info("Showing results for example/mock data. To analyze a real address, enter it and click Analyze.")

# This will show results either from a new search or from cookies
if get_cookie('has_searched') and get_cookie('current_results'):
    # Use the stored data
    data = get_cookie('current_results')
    
    # Display dashboard
    st.markdown("<h1 class='sub-header'>RESULTS</h1>", unsafe_allow_html=True)
    st.markdown("<div style='border-bottom: 1px solid rgba(49, 51, 63, 0.2);'></div>", unsafe_allow_html=True)
    
    # Summary metrics
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    col1, col2, col3, col4, col5 = st.columns(5)
   
    with col1:
        st.metric("Total Transfers", data["summary"]["total_transfers"])
   
    with col2:
        st.metric("Total Tokens", data["summary"]["unique_tokens"])
   
    with col3:
        # Calculate percentage of suspicious transfers
        suspicious_percent = (
            (data["summary"]["suspicious_count"] / data["summary"]["total_transfers"] * 100)
            if data["summary"]["total_transfers"] > 0 else 0
        )
        st.metric(
            "High Risk Transfers",
            data["summary"]["suspicious_count"],
            delta=f"{suspicious_percent:.1f}% of total",
            delta_color="inverse"  # Red for positive (bad)
        )
   
    with col4:
        # Calculate percentage of suspicious tokens
        suspicious_tokens_percent = (
            (data["summary"]["suspicious_tokens"] / data["summary"]["unique_tokens"] * 100)
            if data["summary"]["unique_tokens"] > 0 else 0
        )
        st.metric(
            "High Risk Tokens",
            data["summary"]["suspicious_tokens"],
            delta=f"{suspicious_tokens_percent:.1f}% of total",
            delta_color="inverse"
        )

    with col5:
        # Add new metric for suspicious senders
        suspicious_senders = len(data["suspicious_transfers"]["from_address"].unique()) if not data["suspicious_transfers"].empty else 0
        st.metric(
            "High Risk Senders",
            suspicious_senders
        )
   
    st.markdown("</div>", unsafe_allow_html=True)
   
    # Show suspicious activity section if present
    if data["summary"]["suspicious_count"] > 0:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.markdown("<div style='border-bottom: 1px solid rgba(49, 51, 63, 0.2);'></div>", unsafe_allow_html=True)
        st.subheader("High Risk Tokens Detected")
        
        # Create two columns for metrics and bar chart
        metrics_col, chart_col = st.columns([1, 1])
        
        with metrics_col:
            # Add title for the metrics
            st.markdown("""
                <div style='text-align: left; margin-bottom: 0.5rem;'>
                    <h5 style='margin-bottom: 0.2rem; color: #2d3a4a; text-align: left;'>Tokens by Fraud Type</h5>
                </div>
                """, unsafe_allow_html=True)
            
            # Show tag_1 metrics with modified styling
            tag_df = data["suspicious_tags"]
            if not tag_df.empty:
                st.markdown("<div style='padding-top: 0.2rem;'>", unsafe_allow_html=True)  # Reduced padding
                tag_cols = st.columns(len(tag_df))
                for i, row in tag_df.iterrows():
                    tag_cols[i].metric(row['tag'].title(), int(row['count']))
                st.markdown("</div>", unsafe_allow_html=True)
        
        with chart_col:
            # --- Plotly Interactive Horizontal Stacked Bar Chart with Custom Palette ---
            import plotly.graph_objects as go
            # Custom palette: #102E50, #BE3D2A, #F5C45E
            palette = ['#102E50', '#BE3D2A', '#F5C45E']
            fig = go.Figure()
            for i, row in tag_df.iterrows():
                fig.add_trace(go.Bar(
                    y=["Fraud Types"],
                    x=[row["percent"]],
                    name=row["tag"],
                    orientation="h",
                    marker=dict(color=palette[i % len(palette)]),
                    hovertemplate=f"{row['tag']}: {row['percent']}%<extra></extra>",
                    showlegend=True
                ))
            fig.update_layout(
                barmode='stack',
                height=120,
                margin=dict(l=20, r=20, t=30, b=10),  # Adjusted top margin
                xaxis=dict(range=[0, 100], showgrid=False, showticklabels=False),
                yaxis=dict(showticklabels=False, showgrid=False),
                plot_bgcolor='#f8fafc',
                paper_bgcolor='#f8fafc',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5)
            )
            st.markdown("""
                <div style='text-align: left; margin-bottom: -0.8rem;'>
                    <h5 style='margin-bottom: 0.2rem; color: #2d3a4a; text-align: left;'>Affected Tokens by Fraud Type (%)</h5>
                </div>
                """, unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
   
    # Charts
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.subheader("Token Activity")
        # Bar chart for unique tokens from all and suspicious transfers (Plotly style with custom palette)
        import plotly.graph_objects as go
        tokens_timeline = data["tokens_timeline"]
        x_labels = [d.strftime('%Y-%m-%d') for d in tokens_timeline.index]
        palette = ['#F5C45E', '#BE3D2A']
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=x_labels,
            y=tokens_timeline["All Tokens"],
            name="All Tokens",
            marker_color=palette[0],
            hovertemplate="All Tokens: %{y}<br>Date: %{x}<extra></extra>"
        ))
        fig.add_trace(go.Bar(
            x=x_labels,
            y=tokens_timeline["Suspicious Tokens"],
            name="High Risk Tokens",
            marker_color=palette[1],
            hovertemplate="High Risk Tokens: %{y}<br>Date: %{x}<extra></extra>"
        ))
        fig.update_layout(
            barmode='group',
            height=260,
            margin=dict(l=20, r=20, t=10, b=30),
            xaxis=dict(title='Date', tickangle=-45, tickfont=dict(size=10)),
            yaxis=dict(title='Number of Unique Tokens', gridcolor='rgba(30,41,59,0.08)'),
            plot_bgcolor='#f8fafc',
            paper_bgcolor='#f8fafc',
            legend=dict(orientation='h', yanchor='bottom', y=1.1, xanchor='center', x=0.5)
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with chart_col2:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.subheader("Transfer Activity")
        # Bar chart for all and suspicious transfers (Plotly style with custom palette)
        import plotly.graph_objects as go
        activity_timeline = data["activity_timeline"]
        x_labels = [d.strftime('%Y-%m-%d') for d in activity_timeline.index]
        palette = ['#E78B48', '#BE3D2A']
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=x_labels,
            y=activity_timeline["All Transfers"],
            name="All Transfers",
            marker_color=palette[0],
            hovertemplate="All Transfers: %{y}<br>Date: %{x}<extra></extra>"
        ))
        fig.add_trace(go.Bar(
            x=x_labels,
            y=activity_timeline["Suspicious Transfers"],
            name="High Risk Transfers",
            marker_color=palette[1],
            hovertemplate="High Risk Transfers: %{y}<br>Date: %{x}<extra></extra>"
        ))
        fig.update_layout(
            barmode='group',
            height=260,
            margin=dict(l=20, r=20, t=10, b=30),
            xaxis=dict(title='Date', tickangle=-45, tickfont=dict(size=10)),
            yaxis=dict(title='Number of Transfers', gridcolor='rgba(30,41,59,0.08)'),
            plot_bgcolor='#f8fafc',
            paper_bgcolor='#f8fafc',
            legend=dict(orientation='h', yanchor='bottom', y=1.1, xanchor='center', x=0.5)
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
   
    # Recent transactions with pagination
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)

    # Calculate pagination values
    transfers_per_page = 5  # Number of transfers to show per page
    total_transfers = len(data["recent_transfers"])
    total_pages = (total_transfers + transfers_per_page - 1) // transfers_per_page

    # Create a container for the header and pagination with custom CSS
    st.markdown("""
        <style>
        .header-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        .page-selector {
            width: 100px;
            float: right;
        }
        </style>
    """, unsafe_allow_html=True)

    # Create header with flexbox layout
    st.markdown("""
        <div class="header-container">
            <h3 style="margin: 0;">Recent Transfers</h3>
        </div>
    """, unsafe_allow_html=True)

    # Add page selector in absolute top right
    col1, col2 = st.columns([4, 1])
    with col2:
        current_page = st.selectbox(
            "Page",
            options=range(1, total_pages + 1),
            key="transfer_page",
            label_visibility="collapsed"
        )

    # Calculate start and end indices for current page
    start_idx = (current_page - 1) * transfers_per_page
    end_idx = min(start_idx + transfers_per_page, total_transfers)

    # Add column headers
    header_cols = st.columns([2, 2, 2, 2, 1.5, 1.5, 2, 1.5, 1.5])
    header_cols[0].write("**Tx Hash**")
    header_cols[1].write("**Contract Address**")
    header_cols[2].write("**From Address**")
    header_cols[3].write("**To Address**")
    header_cols[4].write("**Symbol**")
    header_cols[5].write("**Block Timestamp**")
    header_cols[6].write("**Status**")
    header_cols[7].write("**Detail**")
    st.divider()

    # Add transaction rows for current page
    # DEBUG: Print a sample of recent_transfers before rendering
    print("Sample data['recent_transfers'] before rendering:")
    import pandas as pd
    try:
        print(pd.DataFrame(data["recent_transfers"]).head(10)[["from_address", "to_address"]])
    except Exception as e:
        print("DEBUG print failed:", e)
    for row in data["recent_transfers"][start_idx:end_idx]:
        cols = st.columns([2, 2, 2, 2, 1.5, 1.5, 2, 1.5, 1.5])
        cols[0].write(row["tx_hash"])
        cols[1].write(row["contract_address"])
        cols[2].write(row.get("from_address", ""))
        cols[3].write(row.get("to_address", ""))
        cols[4].write(row["symbol"])
        cols[5].write(row.get("block_timestamp", ""))
        # Status badge style
        status = row.get("tag", "Caution")
        status_color = "#b71c1c" if status and status != "Caution" and not row.get("safe", False) else "#2e7d32" if row.get("safe", False) else "#FFD700"  # Changed to yellow (#FFD700)
        status_html = f"""
            <span style='background-color: {status_color}; color: white; padding: 0.2em 0.7em; border-radius: 0.5em; font-size: 0.9em;'>
                {status}
            </span>
        """
        cols[6].markdown(status_html, unsafe_allow_html=True)
        # Detail column (e.g., tag_1)
        detail = row.get("tag_1", "No Detail")
        if detail in ["Fake Stablecoin", "Fake Native", "Phishing"]:
            detail_html = f"""
                <span style='background-color: #b71c1c; color: white; padding: 0.2em 0.7em; border-radius: 0.5em; font-size: 0.9em;'>
                    {detail}
                </span>
            """
            cols[7].markdown(detail_html, unsafe_allow_html=True)
        else:
            cols[7].write(detail)
        st.divider()

    # Add pagination info at the bottom
    st.markdown(f"<div style='text-align: right; color: #666; font-size: 0.8em;'>Showing transfers {start_idx + 1}-{end_idx} of {total_transfers}</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
   
    # Suspicious Tokens Table with pagination
    if data["summary"]["suspicious_count"] > 0:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        
        # Create header with flexbox layout for title and pagination
        st.markdown("""
            <div class="header-container">
                <h3 style="margin: 0;">High Risk Tokens</h3>
            </div>
        """, unsafe_allow_html=True)

        # Add page selector in top right
        susp = data["suspicious_transfers"]
        # Remove duplicate tokens based on contract_address (keep first occurrence)
        susp = susp.drop_duplicates(subset=["contract_address"])
        tokens_per_page = 5  # Number of tokens to show per page
        total_tokens = len(susp)
        total_pages = (total_tokens + tokens_per_page - 1) // tokens_per_page

        col1, col2 = st.columns([4, 1])
        with col2:
            current_page = st.selectbox(
                "Page",
                options=range(1, total_pages + 1),
                key="suspicious_tokens_page",
                label_visibility="collapsed"
            )

        # Calculate start and end indices for current page
        start_idx = (current_page - 1) * tokens_per_page
        end_idx = min(start_idx + tokens_per_page, total_tokens)

        # Display the paginated table with custom style (like Recent Transfers)
        display_cols = ["contract_address", "name", "symbol", "created_block_timestamp", "tag", "tag_1"]
        for col in display_cols:
            if col not in susp.columns:
                susp[col] = ''
        # Table headers
        header_cols = st.columns([3, 2, 3, 2, 2, 2])
        header_cols[0].write("**Contract Address**")
        header_cols[1].write("**Name**")
        header_cols[2].write("**Symbol**")
        header_cols[3].write("**Created Blocktime**")
        header_cols[4].write("**Status**")
        header_cols[5].write("**Detail**")
        st.divider()
        # Table rows
        for _, row in susp.iloc[start_idx:end_idx].iterrows():
            cols = st.columns([3, 2, 3, 2, 2, 2])
            cols[0].write(row["contract_address"])
            cols[1].write(row["name"])
            cols[2].write(row["symbol"])
            cols[3].write(row["created_block_timestamp"])
            # Status badge style (red for high risk, yellow for caution, green for safe)
            status = row.get("tag", "Caution")
            status_color = "#b71c1c" if status and status.lower() not in ["caution", "safe"] else ("#2e7d32" if status.lower() == "safe" else "#FFD700")
            status_html = f"""
                <span style='background-color: {status_color}; color: white; padding: 0.2em 0.7em; border-radius: 0.5em; font-size: 0.9em;'>
                    {status}
                </span>
            """
            cols[4].markdown(status_html, unsafe_allow_html=True)
            # Detail column
            detail = row.get("tag_1", "No Detail")
            if detail in ["Fake Stablecoin", "Fake Native", "Phishing"]:
                detail_html = f"""
                    <span style='background-color: #b71c1c; color: white; padding: 0.2em 0.7em; border-radius: 0.5em; font-size: 0.9em;'>
                        {detail}
                    </span>
                """
                cols[5].markdown(detail_html, unsafe_allow_html=True)
            else:
                cols[5].write(detail)
            st.divider()


else:
    # Welcome message when app loads
    st.markdown("""
    <div class='info-box' style='text-align: center; padding: 2rem;'>
        <h3>Welcome to the Fraud Assessment Tool</h3>
        <p>Enter a blockchain address and select a network to begin your analysis or just use the Try Example button. We will review the last 100 transfers from the past 7 days and check for any suspicious activity.</p>
        <p style='font-size: 0.8rem; margin-top: 2rem;'>
            This tool provides insights into transfers and potentially suspicious token transfers based on a known directory of suspicous contracts.
        </p>
    </div>
    """, unsafe_allow_html=True)
    if 'address' not in st.session_state and 'blockchain' not in st.session_state:
        social_media_icons.render()