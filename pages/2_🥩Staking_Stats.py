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
        label="Unique Delegators",
        value=f"{df_kpi['Unique Delegators'][0]/1000:.1f}k Wallets"
    )

with col2:
    st.metric(
        label="Staking Transactions",
        value=f"{df_kpi['Staking Transactions'][0]/1000:.1f}k Txns"
    )

with col3:
    st.metric(
        label="Avg Transaction per Delegator",
        value=f"{df_kpi['Avg Transaction per Delegator'][0]} Txns"
    )

with col4:
    st.metric(
        label="Unstake Waiting Period",
        value=f"{df_kpi['Unstake Waiting Period'][0]} Days"
    )

# --- Row 3: Action Over Time -------------------------------------------------------------------------------------
@st.cache_data
def load_action_data():
    query = """
    SELECT
        DATE_TRUNC('month', block_timestamp) AS "Date",
        action as "Action",
        round(sum(amount/1e6)) as "Volume (AXL)",
        count(distinct tx_id) as "Transactions"
    FROM axelar.gov.fact_staking
    WHERE tx_succeeded = TRUE 
      AND action IN ('delegate', 'undelegate', 'redelegate')
      AND block_timestamp::date >= '2022-09-01'
    GROUP BY 1, 2
    ORDER BY 1
    """
    return pd.read_sql(query, conn)

df_actions = load_action_data()

# --- نمایش دو نمودار در یک ردیف ---
col1, col2 = st.columns(2)

with col1:
    fig_vol = px.bar(
        df_actions,
        x="Date",
        y="Volume (AXL)",
        color="Action",
        barmode="stack",
        title="Action Volume Over Time (AXL)"
    )
    fig_vol.update_layout(xaxis_title="Date", yaxis_title="Volume (AXL)")
    st.plotly_chart(fig_vol, use_container_width=True)

with col2:
    fig_tx = px.bar(
        df_actions,
        x="Date",
        y="Transactions",
        color="Action",
        barmode="stack",
        title="Action Count Over Time"
    )
    fig_tx.update_layout(xaxis_title="Date", yaxis_title="Transactions")
    st.plotly_chart(fig_tx, use_container_width=True)

# --- Row 4: New vs Returning Stakers + Weekly Volatility ---------------------------------------------------------

# --- Query 1: New vs Returning Stakers
@st.cache_data
def load_staker_data():
    query = """
    WITH first_stake AS (
        SELECT
            delegator_address,
            MIN(block_timestamp) AS first_stake_date
        FROM axelar.gov.fact_staking
        WHERE action = 'delegate' AND tx_succeeded = TRUE
        GROUP BY 1
    ),
    monthly_stakes AS (
        SELECT
            DATE_TRUNC('month', block_timestamp) AS month,
            delegator_address,
            COUNT(*) AS transactions
        FROM axelar.gov.fact_staking
        WHERE action = 'delegate' AND tx_succeeded = TRUE
        GROUP BY 1, 2
    ),
    staker_status AS (
        SELECT
            ws.month,
            ws.delegator_address,
            CASE
                WHEN ws.month = DATE_TRUNC('month', fs.first_stake_date) THEN 'New Staker'
                ELSE 'Returning Staker'
            END AS staker_type,
            ws.transactions
        FROM monthly_stakes ws
        JOIN first_stake fs ON ws.delegator_address = fs.delegator_address
    )
    SELECT
        month as "Date",
        staker_type as "Staker Type",
        COUNT(DISTINCT delegator_address) AS "Staker Count"
    FROM staker_status
    WHERE month >= '2022-09-01'
    GROUP BY 1, 2
    ORDER BY 1
    """
    return pd.read_sql(query, conn)

df_stakers = load_staker_data()

# --- Query 2: Weekly Volatility
@st.cache_data
def load_volatility_data():
    query = """
    SELECT
        DATE_TRUNC('week', block_timestamp) AS "Date",
        round(SUM(amount/1e6)) AS "Total Staked Amount (AXL)",
        STDDEV(SUM(amount/1e6)) OVER (
            ORDER BY DATE_TRUNC('week', block_timestamp)
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS "Weekly Volatility"
    FROM axelar.gov.fact_staking
    WHERE action = 'delegate' AND tx_succeeded = TRUE 
      AND block_timestamp::date >= '2022-09-01'
    GROUP BY 1
    ORDER BY 1
    """
    return pd.read_sql(query, conn)

df_volatility = load_volatility_data()

# --- Layout: Two Charts in a Row
col1, col2 = st.columns(2)

# --- Chart 1: New vs Returning Stakers
with col1:
    fig_stakers = px.bar(
        df_stakers,
        x="Date",
        y="Staker Count",
        color="Staker Type",
        barmode="stack",
        title="New and Returning Stakers Over Time",
        color_discrete_map={
            "Returning Staker": "blue",
            "New Staker": "green"
        }
    )
    fig_stakers.update_layout(xaxis_title="Date", yaxis_title="Staker Count")
    st.plotly_chart(fig_stakers, use_container_width=True)

# --- Chart 2: Weekly Volatility of Staking Amounts
with col2:
    fig_vol = go.Figure()

    # Bar for Total Staked Amount
    fig_vol.add_trace(
        go.Bar(
            x=df_volatility["Date"],
            y=df_volatility["Total Staked Amount (AXL)"],
            name="Total Staked Amount (AXL)",
            yaxis="y1"
        )
    )

    # Line for Weekly Volatility
    fig_vol.add_trace(
        go.Scatter(
            x=df_volatility["Date"],
            y=df_volatility["Weekly Volatility"],
            name="Weekly Volatility",
            mode="lines+markers",
            line=dict(color="red", width=2),
            yaxis="y2"
        )
    )

    # Layout with dual y-axes
    fig_vol.update_layout(
        title="Weekly Volatility of Staking Amounts",
        xaxis=dict(title="Date"),
        yaxis=dict(title="Total Staked Amount (AXL)", side="left"),
        yaxis2=dict(title="Weekly Volatility", overlaying="y", side="right"),
        barmode="group"
    )

    st.plotly_chart(fig_vol, use_container_width=True)

# --- Row 5: Donut Charts by Action -------------------------------------------------------------------------------
@st.cache_data
def load_action_summary():
    query = """
    SELECT
        action,
        COUNT(distinct tx_id) AS "Action Count",
        round(sum(amount)/pow(10,6)) as "Action Amount (AXL)" 
    FROM axelar.gov.fact_staking
    WHERE tx_succeeded = TRUE
    GROUP BY 1
    ORDER BY 2 desc
    """
    return pd.read_sql(query, conn)

df_action_summary = load_action_summary()

# --- Layout: Two Donut Charts in One Row ---
col1, col2 = st.columns(2)

with col1:
    fig_count = px.pie(
        df_action_summary,
        names="ACTION",
        values="Action Count",
        hole=0.5,
        title="Number of Transactions by Action"
    )
    fig_count.update_traces(textinfo="percent+label")
    st.plotly_chart(fig_count, use_container_width=True)

with col2:
    fig_amount = px.pie(
        df_action_summary,
        names="ACTION",
        values="Action Amount (AXL)",
        hole=0.5,
        title="Volume of Transactions by Action (AXL)"
    )
    fig_amount.update_traces(textinfo="percent+label")
    st.plotly_chart(fig_amount, use_container_width=True)

# --- Row 6: Delegator Metrics Table ------------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_delegator_data():
    query = """
    WITH delegator_metrics AS (
        SELECT
            delegator_address,
            SUM(CASE WHEN action = 'delegate' AND tx_succeeded = TRUE THEN amount/1e6 ELSE 0 END) AS total_staked_amount,
            SUM(CASE WHEN action = 'undelegate' AND tx_succeeded = TRUE THEN -amount/1e6 ELSE 0 END) AS total_undelegated_amount,
            SUM(CASE WHEN action = 'redelegate' AND tx_succeeded = TRUE THEN amount/1e6 ELSE 0 END) AS total_redelegated_amount,
            COUNT(*) AS total_transactions,
            COUNT(DISTINCT validator_address) AS unique_validators
        FROM axelar.gov.fact_staking
        GROUP BY delegator_address
    ),
    net_staked AS (
        SELECT
            delegator_address,
            total_staked_amount + total_undelegated_amount AS net_staked_amount
        FROM delegator_metrics
    ),
    total_net_staked AS (
        SELECT
            SUM(net_staked_amount) AS total_net_staked_amount
        FROM net_staked
    ),
    average_transactions AS (
        SELECT
            AVG(total_transactions) AS avg_transactions_per_delegator
        FROM delegator_metrics
    )
    SELECT
        dm.delegator_address as "Delegator",
        round(dm.total_staked_amount) as "Total Staked Amount (AXL)",
        round(dm.total_undelegated_amount) as "Total Unstaked Amount (AXL)",
        round(dm.total_redelegated_amount) as "Total Redelegated Amount (AXL)",
        dm.total_transactions as "Total Transactions",
        dm.unique_validators as "Unique Validators",
        round(ns.net_staked_amount) as "Current Staked Amount",
        round(((ns.net_staked_amount / tns.total_net_staked_amount) * 100),3) || '%' AS "Percentage Of Total Net Staked",
        round(at.avg_transactions_per_delegator) as "Avg Txn Count per Delegator"
    FROM delegator_metrics dm
    JOIN net_staked ns ON dm.delegator_address = ns.delegator_address
    JOIN total_net_staked tns,
         average_transactions at
    ORDER BY 7 DESC
    LIMIT 1000
    """
    return pd.read_sql(query, conn)

df_delegators = load_delegator_data()

# --- KPI Calculation ---
top10 = df_delegators.head(10).copy()

# Current Staked Amount (top 10)
kpi1_value = top10["Current Staked Amount"].sum()

# Percentage of Total Net Staked (top 10)

top10["Percentage_float"] = top10["Percentage Of Total Net Staked"].str.replace("%", "").astype(float)
kpi2_value = top10["Percentage_float"].sum()

# --- KPI Display ---
col1, col2 = st.columns(2)

with col1:
    st.metric(
        label="Total AXL Tokens Staked by the Top 10 Delegators",
        value=f"{kpi1_value:,.0f} AXL"
    )

with col2:
    st.metric(
        label="Top 10 Delegators’ Share of Total Staked AXL Tokens",
        value=f"{kpi2_value:.2f}%"
    )

# --- Table Formatting ---
df_display = df_delegators.copy()

numeric_cols = [
    "Total Staked Amount (AXL)",
    "Total Unstaked Amount (AXL)",
    "Total Redelegated Amount (AXL)",
    "Total Transactions",
    "Unique Validators",
    "Current Staked Amount",
    "Avg Txn Count per Delegator"
]
for col in numeric_cols:
    df_display[col] = df_display[col].apply(lambda x: f"{x:,.0f}")

df_display.index = df_display.index + 1

st.dataframe(df_display, use_container_width=True)
