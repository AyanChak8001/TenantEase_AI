import joblib, pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from src.data.generate_dataset import FEATURES
from src.data.preprocess import load_dataset, validate_features
from src.ml.evaluate import metrics, save_results
from config.settings import MODEL_DIR, REPORT_DIR, MODEL_VERSION, RANDOM_SEED

NUM=[x for x in FEATURES if x not in ["payment_method"]]; CAT=["payment_method"]
def train_model():
    df=load_dataset(); validate_features(df); df=df.sort_values("due_date")
    tenant_numbers=df.tenant_id.str.extract(r"(\d+)")[0].astype(int)
    train_mask=(tenant_numbers<=160) & (df.tenancy_months<=22)
    test_mask=(tenant_numbers>160) & (df.tenancy_months>22)
    X=df[FEATURES]; y=df.late_payment
    pre=ColumnTransformer([("num",Pipeline([("impute",SimpleImputer(strategy="median")),("scale",StandardScaler())]),NUM),("cat",Pipeline([("impute",SimpleImputer(strategy="most_frequent")),("onehot",OneHotEncoder(handle_unknown="ignore"))]),CAT)])
    models={"logistic_regression":LogisticRegression(max_iter=1000,class_weight="balanced",random_state=RANDOM_SEED),"random_forest":RandomForestClassifier(n_estimators=180,max_depth=8,min_samples_leaf=3,class_weight="balanced",random_state=RANDOM_SEED)}
    results={"model_version":MODEL_VERSION,"split":{"train_rows":int(train_mask.sum()),"test_rows":int(test_mask.sum()),"train_tenants":160,"test_tenants":40,"temporal_rule":"test due dates are later than training due dates"},"models":{}}
    for name,est in models.items():
        pipe=Pipeline([("preprocessor",pre),("model",est)]); pipe.fit(X[train_mask],y[train_mask]); prob=pipe.predict_proba(X[test_mask])[:,1]; pred=(prob>=.5).astype(int); results["models"][name]=metrics(y[test_mask],pred,prob)
    baseline=DummyClassifier(strategy="prior"); baseline.fit(X[train_mask],y[train_mask]); baseline_prob=baseline.predict_proba(X[test_mask])[:,1]
    results["baseline_majority"]=metrics(y[test_mask],(baseline_prob>=.5).astype(int),baseline_prob)
    chosen=max(results["models"],key=lambda n:(results["models"][n]["f1"],results["models"][n]["pr_auc"]))
    final=Pipeline([("preprocessor",pre),("model",models[chosen])]); final.fit(X,y); joblib.dump(final,MODEL_DIR/"rent_risk_model.pkl"); save_results({**results,"selected_model":chosen},REPORT_DIR/"evaluation_results.json"); return results

if __name__ == "__main__": print(train_model())
