import optuna
from predict import predict, scan_all_items


N_TRIALS_PER_WORKER = 10
sampler = optuna.samplers.TPESampler()
pruner = optuna.pruners.HyperbandPruner()


def objective(trial):
    from_date = "2022-05-01"
    to_date = "2022-05-10"
    from_date = "2000-01-01"
    to_date = "2100-12-31"
    items = scan_all_items(from_date=from_date, to_date=to_date)
    x = trial.suggest_float("x", -2, 2.0)
    y = trial.suggest_float("y", 0, 0)
    return predict(items, x, y)


if __name__ == "__main__":
    study = optuna.create_study(
        sampler=sampler,
        pruner=pruner,
        direction="maximize",
        study_name="tennis_predfiction",
        storage='sqlite:///../optuna_study.db',
        load_if_exists=True)

    study.optimize(objective, n_trials=N_TRIALS_PER_WORKER)
    # study.optimize(objective, timeout=600)

    print(f"このワーカーが終了した時点で最良の誤差: {study.best_value}")
    print(f"このワーカーが終了した時点で最良のハイパーパラメータ: {study.best_params}")
