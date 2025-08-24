import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.graph_objects as go
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# --- Page Config: Tab Title & Icon ---
st.set_page_config(
    page_title="Axelar Staking and Validators",
    page_icon="https://pbs.twimg.com/profile_images/1877235283755778048/4nlylmxm_400x400.jpg",
    layout="wide" 
)

# --- Title -----------------------------------------------------------------------------------------------------
st.title("🎁Reward Stats")

# --- attention -------------------------------------------------------------------------------------------------
st.info("⏳On-chain data retrieval may take a few moments. Please wait while the results load.")

# --- Sidebar Footer Slightly Left-Aligned ----------------------------------------------------------------------
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

# --- Snowflake Connection --------------------------------------------------------------------------------------
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

# ----------------------- KPI Row -------------------------------------------------------------
@st.cache_data
def load_kpi_data(_conn):
    query = """
    WITH table1 AS (
        SELECT 
            COUNT(DISTINCT delegator_address) AS "Reward Claimers", 
            ROUND(SUM(amount)/POW(10,6)) AS "Reward Claimed",
            COUNT(DISTINCT tx_id) AS "Claim TXs Count"
        FROM axelar.gov.fact_staking_rewards
        WHERE tx_succeeded='true'
    ),
    table2 AS (
        WITH transaction_times AS (
            SELECT
                delegator_address,
                block_timestamp,
                LAG(block_timestamp) OVER (PARTITION BY delegator_address ORDER BY block_timestamp) AS previous_transaction_time
            FROM axelar.gov.fact_staking_rewards
            WHERE tx_succeeded = TRUE
        ),
        time_differences AS (
            SELECT
                delegator_address,
                DATEDIFF(day, previous_transaction_time, block_timestamp) AS time_diff_days
            FROM transaction_times
            WHERE previous_transaction_time IS NOT NULL
        )
        SELECT ROUND(AVG(time_diff_days)) AS "Avg Time Between Transactions Days"
        FROM time_differences
    )
    SELECT * FROM table1, table2
    """
    return pd.read_sql(query, _conn)

df_kpi = load_kpi_data(conn)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Unique Reward Claimers (Wallets)",
        value=f"{df_kpi['Reward Claimers'][0]/1000:.1f}k"
    )

with col2:
    st.metric(
        label="Claim TXs Count (Txns)",
        value=f"{df_kpi['Claim TXs Count'][0]/1000:.1f}k"
    )

with col3:
    st.metric(
        label="Amount of Reward Claimed ($AXL)",
        value=f"{df_kpi['Reward Claimed'][0]/1_000_000:.1f}m"
    )

with col4:
    st.metric(
        label="Avg Time Between Transactions (Days)",
        value=f"{df_kpi['Avg Time Between Transactions Days'][0]} days"
    )

# ----------------------- Time Series Charts --------------------------------------------------
@st.cache_data
def load_timeseries_data(_conn):
    query = """
    SELECT 
        DATE_TRUNC('month',block_timestamp) AS "Date",
        COUNT(DISTINCT delegator_address) AS "Reward Claimers", 
        COUNT(DISTINCT tx_id) AS "Claim TXs Count",
        ROUND(SUM(amount)/POW(10,6)) AS "Reward Claimed (AXL)",
        SUM(ROUND(SUM(amount)/POW(10,6))) OVER (ORDER BY DATE_TRUNC('month',block_timestamp)) 
            AS "Total Reward Claimed (AXL)"
    FROM axelar.gov.fact_staking_rewards
    WHERE tx_succeeded='true' AND block_timestamp::date>='2022-09-01'
    GROUP BY 1
    ORDER BY 1
    """
    return pd.read_sql(query, _conn)

df_ts = load_timeseries_data(conn)

col5, col6 = st.columns(2)

with col5:
    fig1 = go.Figure()
    fig1.add_bar(x=df_ts["Date"], y=df_ts["Reward Claimed (AXL)"], name="Reward Claimed (AXL)")
    fig1.add_trace(go.Scatter(x=df_ts["Date"], y=df_ts["Total Reward Claimed (AXL)"],
                              mode="lines+markers", name="Total Reward Claimed (AXL)", yaxis="y2"))
    fig1.update_layout(
        title="Amount of Reward Claimed Over Time",
        yaxis=dict(title="Reward Claimed (AXL)"),
        yaxis2=dict(title="Total Reward Claimed (AXL)", overlaying="y", side="right")
    )
    st.plotly_chart(fig1, use_container_width=True)

with col6:
    fig2 = go.Figure()
    fig2.add_bar(x=df_ts["Date"], y=df_ts["Claim TXs Count"], name="Claim TXs Count")
    fig2.add_trace(go.Scatter(x=df_ts["Date"], y=df_ts["Reward Claimers"],
                              mode="lines+markers", name="Reward Claimers", yaxis="y2"))
    fig2.update_layout(
        title="Number of Claim Txns & Reward Claimers Over Time",
        yaxis=dict(title="Claim TXs Count"),
        yaxis2=dict(title="Reward Claimers", overlaying="y", side="right")
    )
    st.plotly_chart(fig2, use_container_width=True)

# ----------------------- Validators Table ----------------------------------------------------
@st.cache_data
def load_validators_data(_conn):
    query = """
    SELECT
        b.label AS "Validator Name",
        a.validator_address AS "Validator Address",
        ROUND(SUM(a.amount / 1e6)) AS "Total Rewards Distributed (AXL)"
    FROM axelar.gov.fact_staking_rewards a
    LEFT JOIN axelar.gov.fact_validators b ON a.validator_address = b.address
    WHERE a.tx_succeeded = TRUE
    GROUP BY b.label, a.validator_address
    ORDER BY "Total Rewards Distributed (AXL)" DESC
    LIMIT 75
    """
    return pd.read_sql(query, _conn)

df_val = load_validators_data(conn)
df_val.index = df_val.index + 1  
df_val["Total Rewards Distributed (AXL)"] = df_val["Total Rewards Distributed (AXL)"].apply(lambda x: f"{x:,.0f}")

st.subheader("Validators by Total Rewards Claimed")
st.dataframe(df_val, use_container_width=True)
