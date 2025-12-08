import joblib

model_path = "models/stock_price_regressor_eod.pkl"
pkg = joblib.load(model_path)

print("Selected features:", pkg["selected_features"])
