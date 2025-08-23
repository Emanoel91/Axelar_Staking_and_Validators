import streamlit as st

# --- Page Config: Tab Title & Icon ---
st.set_page_config(
    page_title="Axelar: An overview",
    page_icon="https://img.cryptorank.io/coins/axelar1663924228506.png",
    layout="wide" 
)

# --- Title with Logo ------------------------------------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="display: flex; align-items: center; gap: 15px;">
        <img src="https://img.cryptorank.io/coins/axelar1663924228506.png" alt="Axelar Logo" style="width:60px; height:60px;">
        <h1 style="margin: 0;">Axelar: An overview</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Reference and Rebuild Info -------------------------------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="margin-top: 20px; margin-bottom: 20px; font-size: 16px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://pbs.twimg.com/profile_images/1841479747332608000/bindDGZQ_400x400.jpg" alt="Eman Raz" style="width:25px; height:25px; border-radius: 50%;">
            <span>Built by: <a href="https://x.com/0xeman_raz" target="_blank">Eman Raz</a></span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Info Box -----------------------------------------------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="background-color: #cff1e4; padding: 15px; border-radius: 10px; border: 1px solid #cff1e4;">
        Axelar emerges as the cutting-edge platform revolutionizing Web3 interoperability, poised to propel the next wave of internet applications to unparalleled heights, 
        accommodating billions of users worldwide. With its innovative architecture and robust infrastructure, Axelar paves the way for seamless connectivity across diverse 
        blockchain networks, facilitating frictionless data and asset transfer while ensuring utmost security and efficiency.
        At its core, Axelar serves as the bridge between disparate blockchain ecosystems, enabling developers to harness the full potential of decentralized applications (dApps) 
        without constraints. By offering a programmable framework, Axelar empowers developers to effortlessly integrate their applications with multiple blockchains, unlocking 
        unprecedented scalability and accessibility on a global scale.
        In a landscape where interoperability is paramount, Axelar stands as the beacon of innovation, driving forward the vision of a truly interconnected Web3 ecosystem. 
        
</div>
    """,
    unsafe_allow_html=True
)

# --- Reference Info ------------------------------------------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="margin-top: 20px; margin-bottom: 20px; font-size: 16px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://pbs.twimg.com/profile_images/1856738793325268992/OouKI10c_400x400.jpg" alt="Flipside" style="width:25px; height:25px; border-radius: 50%;">
            <span>Data Powered by: <a href="https://flipsidecrypto.xyz/home/" target="_blank">Flipside</a></span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Links with Logos ---
st.markdown(
    """
    <div style="font-size: 16px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://axelarscan.io/logos/logo.png" alt="Axelar" style="width:20px; height:20px;">
            <a href="https://www.axelar.network/" target="_blank">Axelar Website</a>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://axelarscan.io/logos/logo.png" alt="Axelar" style="width:20px; height:20px;">
            <a href="https://x.com/axelar" target="_blank">Axelar X Account</a>
        </div>
        
    </div>
    """,
    unsafe_allow_html=True
)

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
