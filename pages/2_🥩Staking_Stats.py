import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.graph_objects as go
import plotly.express as px
import plotly.graph_objects as go
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import requests

# --- Page Config: Tab Title & Icon ---
st.set_page_config(
    page_title="Axelar Staking and Validators",
    page_icon="https://pbs.twimg.com/profile_images/1877235283755778048/4nlylmxm_400x400.jpg",
    layout="wide" 
)
# --- Title  -----------------------------------------------------------------------------------------------------
st.title("🥩Staking Stats")

# --- attention ---------------------------------------------------------------------------------------------------------
st.info("📊Charts initially display data for a default time range. Select a custom range to view results for your desired period.")
st.info("⏳On-chain data retrieval may take a few moments. Please wait while the results load.")

# --- Sidebar Footer Slightly Left-Aligned ---
st.sidebar.markdown(
    """
    <style>
    .sidebar-footer {
        position: fixed;
        bottom: 20px;
        width: 250px;
        font-size: 13px;
        color: gray;
        margin-left: 5px; # -- MOVE LEFT
        text-align: left;  
    }
    .sidebar-footer img {
        width: 16px;
        height: 16px;
        vertical-align: middle;
        border-radius: 50%;
        margin-right: 5px;
    }
    .sidebar-footer a {
        color: gray;
        text-decoration: none;
    }
    </style>

    <div class="sidebar-footer">
        <div>
            <a href="https://x.com/axelar" target="_blank">
                <img src="https://img.cryptorank.io/coins/axelar1663924228506.png" alt="Axelar Logo">
                Powered by Axelar
            </a>
        </div>
        <div style="margin-top: 5px;">
            <a href="https://x.com/0xeman_raz" target="_blank">
                <img src="https://pbs.twimg.com/profile_images/1841479747332608000/bindDGZQ_400x400.jpg" alt="Eman Raz">
                Built by Eman Raz
            </a>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Snowflake Connection ----------------------------------------------------------------------------------------
snowflake_secrets = st.secrets["snowflake"]
user = snowflake_secrets["user"]
account = snowflake_secrets["account"]
private_key_str = snowflake_secrets["private_key"]
warehouse = snowflake_secrets.get("warehouse", "")
database = snowflake_secrets.get("database", "")
schema = snowflake_secrets.get("schema", "")

private_key_pem = f"-----BEGIN PRIVATE KEY-----\n{private_key_str}\n-----END PRIVATE KEY-----".encode("utf-8")
private_key = serialization.load_pem_private_key(
    private_key_pem,
    password=None,
    backend=default_backend()
)
private_key_bytes = private_key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

conn = snowflake.connector.connect(
    user=user,
    account=account,
    private_key=private_key_bytes,
    warehouse=warehouse,
    database=database,
    schema=schema
)

# ---------- Query Snowflake ----------

query = """
WITH staking_actions AS (
    SELECT
        delegator_address,
        validator_address,
        action,
        amount, CASE
            WHEN action = 'delegate' THEN amount
            WHEN action = 'undelegate' THEN -amount
            ELSE 0
        END AS net_amount
    FROM
        axelar.gov.fact_staking
    WHERE
        tx_succeeded = TRUE
),

net_staking AS (
    SELECT
        SUM(net_amount/1e6) AS total_staked
    FROM
        staking_actions
)

SELECT
    ROUND(ns.total_staked) AS currently_staked_axl
FROM
    net_staking ns
"""

df = pd.read_sql(query, conn)
currently_staked_axl = df["CURRENTLY_STAKED_AXL"].iloc[0]  # عدد AXL استیک شده

# ---------- Call APIs ----------
supply_url = "https://api.axelarscan.io/api/getTotalSupply"
price_url = "https://api.axelarscan.io/api/getTokensPrice?symbol=AXL"

total_supply = float(requests.get(supply_url).json()) / 1e6  # تبدیل به میلیون
price_axl = requests.get(price_url).json()["AXL"]["price"]

# ---------- KPIs ----------
currently_staked_m = currently_staked_axl / 1e6  # به میلیون
currently_staked_usd_m = (currently_staked_axl * price_axl) / 1e6
percent_staked = (currently_staked_axl / (total_supply * 1e6)) * 100

# ---------- Display in Streamlit ----------
st.markdown("## 🔑 Key Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Currently Staked Amount",
        value=f"{currently_staked_m:,.2f}m $AXL"
    )

with col2:
    st.metric(
        label="Currently Staked Amount (USD)",
        value=f"${currently_staked_usd_m:,.2f}m"
    )

with col3:
    st.metric(
        label="Currently Total Supply",
        value=f"{total_supply:,.2f}m $AXL"
    )

with col4:
    st.metric(
        label="% of Total Supply Staked",
        value=f"{percent_staked:.2f}%"
    )

# --- Row 2 ----------------------------------------------------------------------------------------------------
@st.cache_data
def load_kpi_data():
    query = """
    WITH tab1 AS (
        SELECT
            count(distinct delegator_address) AS "Unique Delegators",
            count(distinct tx_id) AS "Staking Transactions",
            round(count(distinct tx_id)/count(distinct delegator_address)) as "Avg Transaction per Delegator"
        FROM axelar.gov.fact_staking
        WHERE action IN ('delegate') AND tx_succeeded = TRUE
    ),
    tab2 AS (
        SELECT
            round(AVG(DATEDIFF(day, block_timestamp, completion_time))) AS "Unstake Waiting Period"
        FROM axelar.gov.fact_staking
        WHERE action IN ('undelegate') AND tx_succeeded = TRUE
        GROUP BY action
    )
    SELECT * FROM tab1 , tab2
    """
    return pd.read_sql(query, conn)

df_kpi = load_kpi_data()

# --- kpi in 1 row --------------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Unique Delegators (Wallets)",
        value=f"{df_kpi['Unique Delegators'][0]/1000:.1f}k"
    )

with col2:
    st.metric(
        label="Staking Transactions (Txns)",
        value=f"{df_kpi['Staking Transactions'][0]/1000:.1f}k"
    )

with col3:
    st.metric(
        label="Avg Transaction per Delegator (Txns)",
        value=f"{df_kpi['Avg Transaction per Delegator'][0]}"
    )

with col4:
    st.metric(
        label="Unstake Waiting Period (Days)",
        value=f"{df_kpi['Unstake Waiting Period'][0]}"
    )

