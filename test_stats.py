import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# Load the CSV
df = pd.read_csv('baseball_stats.csv', encoding='utf-8')

# Drop non-numeric or irrelevant columns (like names or awards for now)
df = df.drop(['Rk', 'Player', 'Team', 'Lg', 'Pos', 'Awards'], axis=1, errors='ignore')

# Optional: Encode any remaining non-numeric columns
for col in df.columns:
    if df[col].dtype == 'object':
        df[col] = LabelEncoder().fit_transform(df[col])

# Drop rows with missing values (simplest strategy)
df = df.dropna()

# Separate features and target
X = df.drop('WAR', axis=1)
y = df['WAR']

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Create and train model
model = XGBRegressor()
model.fit(X_train, y_train)

# Predict
predictions = model.predict(X_test)
print(predictions)
