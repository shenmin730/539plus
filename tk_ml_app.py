import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score, classification_report
import threading
from excel import load_history_data

class DataLoader:
    def load_history(self):
        return load_history_data(window=30)   # 你可以調 window 長度

class ModelTrainer:
    def __init__(self, data_loader, features, target='number', cv=5):
        self.loader = data_loader
        self.features = features
        self.target = target
        self.cv = cv
        self.model = None

    def prepare_data(self):
        df = self.loader.load_history()
        X = df[self.features]
        y = df[self.target]
        return train_test_split(X, y, test_size=0.2, random_state=42)

    def train(self):
        X_train, X_test, y_train, y_test = self.prepare_data()
        # 自動調參範圍
        param_grid = {
            'n_estimators': [50,100,200],
            'max_depth': [5,10,20],
            'min_samples_split': [2,5,10]
        }
        base = RandomForestClassifier(random_state=42)
        gs = GridSearchCV(base, param_grid, cv=self.cv, n_jobs=-1)
        gs.fit(X_train, y_train)
        self.model = gs.best_estimator_

        preds = self.model.predict(X_test)
        acc = accuracy_score(y_test, preds)
        report = classification_report(y_test, preds, zero_division=0)
        return gs.best_params_, acc, report

    def predict_next(self, features_df):
        prob = self.model.predict_proba(features_df)[0]
        return list(zip(self.model.classes_, prob))

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("539 ML Predictor (Optimized)")
        self.geometry("450x550")

        self.features = [
            'sum','span','odd_even_ratio','prime_count',
            'high_low_ratio','consecutive_pairs','gap_mean','recent_count'
        ]
        self.loader = DataLoader()
        self.trainer = ModelTrainer(self.loader, self.features)

        ttk.Button(self, text="訓練並調參", command=self.train_model).pack(pady=10)
        self.txt = tk.Text(self, height=15)
        self.txt.pack(fill=tk.BOTH, padx=10)
        ttk.Button(self, text="推薦號碼", command=self.recommend).pack(pady=10)

    def train_model(self):
        def job():
            best_params, acc, report = self.trainer.train()
            out = f"最佳參數: {best_params}\n測試集準確率: {acc:.3f}\n\n" + report
            self.txt.delete(1.0, tk.END)
            self.txt.insert(tk.END, out)
        threading.Thread(target=job).start()

    def recommend(self):
        df = self.loader.load_history()
        last = df.tail(1)[self.features]
        results = self.trainer.predict_next(last)
        top5 = sorted(results, key=lambda x: x[1], reverse=True)[:5]
        msg = "推薦號碼 (機率)：\n" + "\n".join(f"{n}: {p:.3f}" for n,p in top5)
        messagebox.showinfo("推薦結果", msg)

if __name__ == '__main__':
    app = App()
    app.mainloop()
