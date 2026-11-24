import numpy as np
from sklearn.linear_model import Lasso
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

FOLDS = 4

def features(row):
    return [row[key] for key in ('heat', 'thick', 'target')]

def split(history):
    archive = sorted(history, key=lambda row: row['heat'])
    holdout = [row for index, row in enumerate(archive) if index % 4 == 0]
    train = [row for index, row in enumerate(archive) if index % 4 != 0]
    return train, holdout

def fit(train, penalty):
    model = make_pipeline(PolynomialFeatures(degree=2, include_bias=False),
                          StandardScaler(), Lasso(alpha=penalty, max_iter=20000))
    model.fit([features(row) for row in train], [row['measured'] for row in train])
    return model

def mae(model, rows):
    errors = model.predict([features(row) for row in rows]) - [row['measured'] for row in rows]
    return float(np.mean(np.abs(errors)))

def terms_of(model):
    terms = model[0].get_feature_names_out(['温度','片厚','目标弯度'])
    return [term for term, coef in zip(terms, model[-1].coef_) if abs(coef) > 1e-10]

def cv_mae(train, penalty):
    ordered = sorted(train, key=lambda row: row['heat'])
    scores = []
    for turn in range(FOLDS):
        held = [row for index, row in enumerate(ordered) if index % FOLDS == turn]
        rest = [row for index, row in enumerate(ordered) if index % FOLDS != turn]
        scores.append(mae(fit(rest, penalty), held))
    return float(np.mean(scores))

def calculate(data):
    train, holdout = split(data['history'])
    model = fit(train, data['penalty'])
    return {'prediction': round(float(model.predict([features(data['coupon'])])[0]),3),
            'mae': round(mae(model, holdout),3), 'held_out': len(holdout),
            'terms': terms_of(model)}

def sweep(data, cached, checkpoint):
    train, holdout = split(data['history'])
    scores = {float(penalty): float(score) for penalty, score in cached.items()}
    for penalty in sorted(data['penalties']):
        if penalty in scores:
            continue
        scores[penalty] = round(cv_mae(train, penalty), 3)
        checkpoint(penalty, scores[penalty])
    winner = min(scores, key=lambda penalty: (scores[penalty], penalty))
    model = fit(train, winner)
    return {'prediction': round(float(model.predict([features(data['coupon'])])[0]),3),
            'mae': round(mae(model, holdout),3), 'held_out': len(holdout),
            'terms': terms_of(model), 'penalty': winner,
            'tiers': [{'penalty': penalty, 'cv_mae': scores[penalty]} for penalty in sorted(scores)],
            'grouping': {'train': [row['code'] for row in train],
                         'holdout': [row['code'] for row in holdout]}}
