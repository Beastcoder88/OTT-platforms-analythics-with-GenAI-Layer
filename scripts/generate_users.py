from pathlib import Path
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)   # fixed seed = same data every run

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "generated"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------- Rules (from docs/schema_design.md) ----------
N_NORMAL = 4400        # regular signups
N_SPIKE = 600          # extra signups during the cricket window
DATA_START = pd.Timestamp("2025-01-01")
DATA_END = pd.Timestamp("2025-12-31")
SPIKE_START = pd.Timestamp("2025-04-10")
SPIKE_END = pd.Timestamp("2025-04-24")
SIGNUP_FROM = pd.Timestamp("2024-07-01")   # some users joined before the data year
SIGNUP_TO = pd.Timestamp("2025-11-30")

REGIONS = ["Delhi", "Mumbai", "Bengaluru", "Chennai", "Hyderabad", "Kolkata"]
REGION_P = [0.22, 0.20, 0.17, 0.15, 0.13, 0.13]
MAIN_LANGUAGE = {
    "Delhi": "Hindi", "Mumbai": "Hindi", "Bengaluru": "English",
    "Chennai": "Tamil", "Hyderabad": "Telugu", "Kolkata": "Bengali",
}
TIERS = ["Free", "Mobile", "Standard", "Premium"]   # simulated tiers
TIER_P = [0.40, 0.25, 0.20, 0.15]
CHURN_P = {"Free": 0.22, "Mobile": 0.15, "Standard": 0.10, "Premium": 0.06}
SPIKE_CHURN_P = 0.60   # spike signups churn more, and faster

# ---------- Signup dates ----------
normal_days = (SIGNUP_TO - SIGNUP_FROM).days
spike_days = (SPIKE_END - SPIKE_START).days

normal_signup = SIGNUP_FROM + pd.to_timedelta(rng.integers(0, normal_days + 1, N_NORMAL), unit="D")
spike_signup = SPIKE_START + pd.to_timedelta(rng.integers(0, spike_days + 1, N_SPIKE), unit="D")

users = pd.DataFrame({
    "signup_date": np.concatenate([normal_signup.values, spike_signup.values]),
    "is_spike": np.array([False] * N_NORMAL + [True] * N_SPIKE),
})
users = users.sample(frac=1, random_state=42).reset_index(drop=True)   # shuffle
users.insert(0, "user_id", users.index + 1)
n = len(users)

# ---------- Region, language, tier ----------
users["region"] = rng.choice(REGIONS, n, p=REGION_P)
users["subscription_tier"] = rng.choice(TIERS, n, p=TIER_P)

def pick_language(region):
    if rng.random() < 0.7:
        return MAIN_LANGUAGE[region]
    return rng.choice(["Hindi", "English"])

users["preferred_language"] = users["region"].apply(pick_language)

# ---------- Churn (cancel_date) ----------
# Users who joined before the data year are treated as starting on DATA_START.
anchor = users["signup_date"].clip(lower=DATA_START)

p_churn = np.where(users["is_spike"], SPIKE_CHURN_P, users["subscription_tier"].map(CHURN_P))
churned = rng.random(n) < p_churn

offset_days = np.where(users["is_spike"], rng.integers(10, 46, n), rng.integers(30, 301, n))
cancel = anchor + pd.to_timedelta(offset_days, unit="D")
cancel = cancel.where(churned)              # NaT for users who don't churn
cancel = cancel.where(cancel <= DATA_END)   # cancellations after the data year = still active
users["cancel_date"] = cancel

# ---------- Save ----------
cols = ["user_id", "region", "preferred_language", "subscription_tier", "signup_date", "cancel_date"]
users[cols].to_csv(OUT_DIR / "users.csv", index=False, date_format="%Y-%m-%d")

# ---------- Quick checks ----------
print("Users:", n)
print("Overall churn %:", round(users["cancel_date"].notna().mean() * 100, 1))
print("Spike-signup churn %:", round(users.loc[users["is_spike"], "cancel_date"].notna().mean() * 100, 1))
print("\nChurn % by tier:")
print(users.groupby("subscription_tier")["cancel_date"].apply(lambda s: round(s.notna().mean() * 100, 1)))
print("\nSignups per month:")
print(users["signup_date"].dt.to_period("M").value_counts().sort_index())