import json
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix, brier_score_loss

def metrics(y, pred, prob):
    return {"accuracy":float(accuracy_score(y,pred)),"precision":float(precision_score(y,pred,zero_division=0)),"recall":float(recall_score(y,pred,zero_division=0)),"f1":float(f1_score(y,pred,zero_division=0)),"roc_auc":float(roc_auc_score(y,prob)),"pr_auc":float(average_precision_score(y,prob)),"brier_score":float(brier_score_loss(y,prob)),"confusion_matrix":confusion_matrix(y,pred).tolist()}

def save_results(results, path):
    path.write_text(json.dumps(results, indent=2))
