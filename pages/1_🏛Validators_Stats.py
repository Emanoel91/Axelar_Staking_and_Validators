import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.graph_objects as go
import plotly.express as px
import plotly.graph_objects as go
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# --- Page Config: Tab Title & Icon ---
st.set_page_config(
    page_title="Axelar Staking and Validators",
    page_icon="https://pbs.twimg.com/profile_images/1877235283755778048/4nlylmxm_400x400.jpg",
    layout="wide" 
)
# --- Title  -----------------------------------------------------------------------------------------------------
st.title("🏛Validators Stats")

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

# --- Queries with st.cache_data --------------------------------------------------------------------------------
# --- Row 1 -----------------------------------------------------------------------------------------------------
@st.cache_data
def load_kpi_data():
    query = """
    SELECT 
        round((SUM(DELEGATOR_SHARES)),1) AS "Total Delegator Shares", 
        75 as "Active Validators", 
        COUNT(DISTINCT ADDRESS) AS "Total Validators"
    FROM axelar.gov.fact_validators
    """
    return pd.read_sql(query, conn)

# --- KPI Section 1 --------------------------------------------------------------------------------
kpi_df = load_kpi_data()
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Number of Validators", int(kpi_df["Total Validators"].iloc[0]))
with col2:
    st.metric("Number of Active Validators", int(kpi_df["Active Validators"].iloc[0]))
with col3:
    total_shares_m = kpi_df["Total Delegator Shares"].iloc[0] / 1_000_000
    st.metric("Total Delegator Shares", f"{total_shares_m:,.1f}m $AXL")

# --- Row 2 -----------------------------------------------------------------------------------------------------------------
@st.cache_data(ttl=600)
def load_validators_amounts():
    query = """
    WITH Amount AS (
        SELECT 
            VALIDATOR_ADDRESS,
            SUM(amount) / 1e6 AS balance
        FROM (
            SELECT 
                BLOCK_TIMESTAMP,
                VALIDATOR_ADDRESS, 
                CASE 
                    WHEN action = 'undelegate' THEN -amount
                    ELSE amount 
                END AS amount
            FROM axelar.gov.fact_staking

            UNION ALL

            SELECT 
                BLOCK_TIMESTAMP,
                REDELEGATE_SOURCE_VALIDATOR_ADDRESS, 
                -amount
            FROM axelar.gov.fact_staking
            WHERE action = 'redelegate'
        )
        GROUP BY VALIDATOR_ADDRESS
    ),
    Delegations AS (
        SELECT 
            VALIDATOR_ADDRESS,
            DELEGATOR_ADDRESS,
            SUM(amount) / 1e6 AS total_delegated
        FROM axelar.gov.fact_staking
        WHERE action = 'delegate'
        GROUP BY VALIDATOR_ADDRESS, DELEGATOR_ADDRESS
    )
    SELECT  
        v.label AS "Validator Name",
        round(a.balance,1) AS "Total Delegated Amount (AXL)",
        COUNT(DISTINCT d.DELEGATOR_ADDRESS) AS "Unique Delegators"
    FROM Amount a
    JOIN axelar.gov.fact_validators v ON a.VALIDATOR_ADDRESS = v.ADDRESS
    JOIN Delegations d ON a.VALIDATOR_ADDRESS = d.VALIDATOR_ADDRESS
    GROUP BY 1,2
    ORDER BY 2 DESC
    LIMIT 75
    """
    return pd.read_sql(query, conn)

# --- Charts Section 1: Delegated Amount & Unique Delegators ----------------------------------------
validators_df = load_validators_amounts()
col1, col2 = st.columns(2)

with col1:
    fig1 = px.bar(
        validators_df.sort_values("Total Delegated Amount (AXL)", ascending=True),
        x="Total Delegated Amount (AXL)",
        y="Validator Name",
        orientation="h",
        title="Top Active Validators by Delegated Amount"
    )
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    fig2 = px.bar(
        validators_df.sort_values("Unique Delegators", ascending=True),
        x="Unique Delegators",
        y="Validator Name",
        orientation="h",
        title="Top Active Validators by No. of Unique Delegators"
    )
    st.plotly_chart(fig2, use_container_width=True)

# --- Row 3 -------------------------------------------------------------------------------------------------------------------
@st.cache_data(ttl=600)
def load_commission_stats():
    query = """
    with tab1 as (
    SELECT round(AVG(RATE),2) * 100 AS "Average Commission Rate", 
    MAX(RATE) * 100 AS "Maximum Commission Rate"
    FROM axelar.gov.fact_validators),

    TAB2 AS (
    SELECT round((SUM(AMOUNT)/1e6),2) AS "Total Commission Amount", 
    round((AVG(AMOUNT)/1e6),2) AS "Average Commission Amount"
    FROM axelar.gov.fact_validator_commission)

    SELECT * FROM tab1 , tab2
    """
    return pd.read_sql(query, conn)

# --- KPI Section 2: Commission Stats ---------------------------------------------------------------
commission_df = load_commission_stats()
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Max Commission Rate", f"{commission_df['Maximum Commission Rate'].iloc[0]} %")
with col2:
    st.metric("Avg Commission Rate", f"{commission_df['Average Commission Rate'].iloc[0]} %")
with col3:
    total_commission_m = commission_df["Total Commission Amount"].iloc[0] / 1_000_000
    st.metric("Total Commission Amount Claimed", f"{total_commission_m:,.1f}m $AXL")
with col4:
    st.metric("Average Commission Claimed", f"{commission_df['Average Commission Amount'].iloc[0]} $AXL")


# --- Row 4 ----------------------------------------------------------------------------------
@st.cache_data(ttl=600)
def load_commission_claimed():
    query = """
    SELECT 
        b.label AS "Validator Name",
        ROUND(SUM(a.AMOUNT / 1e6),1) AS "Total Commission Claimed (AXL)"
    FROM 
        axelar.gov.fact_validator_commission a
        LEFT JOIN axelar.gov.fact_validators b ON a.validator_address_operator = b.address
    GROUP BY 1
    ORDER BY 2 DESC
    LIMIT 75
    """
    return pd.read_sql(query, conn)

@st.cache_data(ttl=600)
def load_commission_rates():
    query = """
    WITH Amount AS (
        SELECT 
            VALIDATOR_ADDRESS,
            SUM(amount) / 1e6 AS balance
        FROM (
            SELECT 
                BLOCK_TIMESTAMP,
                VALIDATOR_ADDRESS, 
                CASE 
                    WHEN action = 'undelegate' THEN -amount
                    ELSE amount 
                END AS amount
            FROM axelar.gov.fact_staking

            UNION ALL

            SELECT 
                BLOCK_TIMESTAMP,
                REDELEGATE_SOURCE_VALIDATOR_ADDRESS, 
                -amount
            FROM axelar.gov.fact_staking
            WHERE action = 'redelegate'
        )
        GROUP BY VALIDATOR_ADDRESS
    ),
    Delegations AS (
        SELECT 
            VALIDATOR_ADDRESS,
            DELEGATOR_ADDRESS,
            SUM(amount) / 1e6 AS total_delegated
        FROM axelar.gov.fact_staking
        WHERE action = 'delegate'
        GROUP BY VALIDATOR_ADDRESS, DELEGATOR_ADDRESS
    )
    SELECT  
        distinct v.label AS "Validator Name",
        v.rate * 100 AS "Commission Rate %"
    FROM Amount a
    JOIN axelar.gov.fact_validators v ON a.VALIDATOR_ADDRESS = v.ADDRESS
    JOIN Delegations d ON a.VALIDATOR_ADDRESS = d.VALIDATOR_ADDRESS
    ORDER BY 2 DESC
    LIMIT 75
    """
    return pd.read_sql(query, conn)

# --- Charts Section 2: Commission Claimed & Commission Rate ----------------------------------------
commission_claimed_df = load_commission_claimed()
commission_rate_df = load_commission_rates()
col1, col2 = st.columns(2)

with col1:
    fig3 = px.bar(
        commission_claimed_df.sort_values("Total Commission Claimed (AXL)", ascending=True),
        x="Total Commission Claimed (AXL)",
        y="Validator Name",
        orientation="h",
        title="Top Active Validators by Commission Claimed"
    )
    st.plotly_chart(fig3, use_container_width=True)

with col2:
    fig4 = px.bar(
        commission_rate_df.sort_values("Commission Rate %", ascending=True),
        x="Commission Rate %",
        y="Validator Name",
        orientation="h",
        title="Top Active Validators by Commission Rate"
    )
    st.plotly_chart(fig4, use_container_width=True)
