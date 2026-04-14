import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
from sklearn.metrics import mean_absolute_error

from analisys.GroupData import F125_TelemetryConsolidated

class John:
    def __init__(self, track:str, session:str, num_laps:int = 3):
        self.track = track
        self.session = session
        
        self.tyre_rolling_range = [5, 10, 15, 20, 25]

        self.tyre_wear_columns = ['tyresWearFL', 'tyresWearFR', 'tyresWearRL', 'tyresWearRR']
        self.tyre_surface_temp_columns = ['tyresSurfaceTemperatureFL', 'tyresSurfaceTemperatureFR', 'tyresSurfaceTemperatureRL', 'tyresSurfaceTemperatureRR']
        
        self.models_path = f"analisys/models/{track}/{session}"
        self.df = None
        self.benchmark_laps = None

        try:
            self.loadReferenceLaps(df=self.df, num_laps=num_laps)
        except Exception as e:
            raise RuntimeError(f"Error loading reference laps: {e}")

        try:
            self.X_train, self.X_test, self.y_train, self.y_test = self.splitTestTrain()
        except Exception as e:
            raise RuntimeError(f"Error splitting train/test: {e}")

        try:
            self.normalizedFeatures()
        except Exception as e:
            raise RuntimeError(f"Error normalizing features: {e}")

        try:
            self.applyRegressor()
        except Exception as e:
            raise RuntimeError(f"Error applying regressor: {e}")

        try:
            self.setFeatureImportance()
        except Exception as e:
            raise RuntimeError(f"Error setting feature importance: {e}")

        try:
            self.saveTrainedModels()
        except Exception as e:
            raise RuntimeError(f"Error saving trained models: {e}")
        
    def loadRawParquet(self):
        self.df = pd.read_parquet(f"analisys/sanitazed_data/{self.track}/{self.session}/{self.parquet_path}")
        self.df = self.derivedFeatures(self.df)
        
    def derivedFeatures(self, df):
        df = df.sort_values(['lap', 'lapDistance']).reset_index(drop=True)
        
        df["avg_tyre_wear"] = df[self.tyre_wear_columns].mean(axis=1)

        diff_tyre_wear_columns = []
        for i in self.tyre_rolling_range:
            df[f"avg_diff_tyre_wear_{i}"] = df["avg_tyre_wear"] - df["avg_tyre_wear"].rolling(window=i).mean().fillna(0)
            diff_tyre_wear_columns.append(f"avg_diff_tyre_wear_{i}")    
            
        if len(diff_tyre_wear_columns) > 0:
            df["avg_diff_tyre_wear"] = df[diff_tyre_wear_columns].mean(axis=1)

        df["avg_tyre_surface_temp"] = df[self.tyre_surface_temp_columns].mean(axis=1)

        diff_tyre_surface_temp_columns = []
        for i in self.tyre_rolling_range:
            df[f"avg_diff_tyre_surface_temp_{i}"] = df["avg_tyre_surface_temp"] - df["avg_tyre_surface_temp"].rolling(window=i).mean().fillna(0)
            diff_tyre_surface_temp_columns.append(f"avg_diff_tyre_surface_temp_{i}")
            
        if len(diff_tyre_surface_temp_columns) > 0:
            df["avg_diff_tyre_surface_temp"] = df[diff_tyre_surface_temp_columns].mean(axis=1)    
            
        df["is_corner"] = (
            (df["steer"].abs() > 0.5) |
            (df["gForceLateral"].abs() > 2.0)
        )        

        df["steer_filtered"] = df["steer"].where(df["steer"].abs() > 0.1, 0)
        df["steer_sign"] = np.sign(df["steer_filtered"])

        df["direction_change"] = df["steer_sign"] != df["steer_sign"].shift(1)

        df["direction_change"] = (
            (df["gForceLateral"] * df["gForceLateral"].shift(1)) < 0
        )

        df["corner_start"] = (
            (df["is_corner"]) & (
                (~df["is_corner"].shift(1, fill_value=False)) |  # entrou na curva
                (df["direction_change"])                         # ou mudou direção (slalom)
            )
        )

        df = df.drop(columns=["direction_change", "is_corner"] + diff_tyre_surface_temp_columns + diff_tyre_wear_columns)

        df["corner_id"] = df["corner_start"].cumsum()

        df['power_efficiency'] = df['speed'] / (df['engineRPM'] + 1)

        df['lap_progress'] = df.groupby('lap').cumcount() / df.groupby('lap')['lap'].transform('count')

        return df
    
    def loadReferenceLaps(self, df, num_laps:int = 3):
        voltas_no_pit = df[df['pitStatus'] == 1]['lap'].unique()
        df_filtrado = df[~df['lap'].isin(voltas_no_pit)]

        self.lap_stats = df_filtrado.groupby('lap').agg({
            'speed': ['mean', 'std'],
            'throttle': 'mean',
            'brake': 'mean',
            'power_efficiency': 'mean',
            'avg_diff_tyre_surface_temp': 'mean',
            'avg_diff_tyre_wear': 'mean',
            'corner_id': 'count',
            'lap_progress': 'count'
        }).reset_index()

        self.lap_stats.columns = [
            'lap', 'avg_speed', 'std_speed', 'avg_throttle', 'avg_brake',
            'avg_power_efficiency', 'avg_tyre_surface_temp', 'avg_tyre_wear',
            'corder_id', 'lap_progress'
        ]

        self.lap_stats['speed_score'] = ((
            self.lap_stats['avg_speed'] - self.lap_stats['avg_speed'].min()) / 
            (self.lap_stats['avg_speed'].max() - self.lap_stats['avg_speed'].min()
        ))
                                        
        self.lap_stats['consistency_score'] = (
            1 - ((self.lap_stats['std_speed'] - self.lap_stats['std_speed'].min()) / 
                (self.lap_stats['std_speed'].max() - self.lap_stats['std_speed'].min() + 0.001))
        )

        self.lap_stats['tyre_surface_temp_score'] = (
            1 - ((self.lap_stats['avg_tyre_surface_temp'] - self.lap_stats['avg_tyre_surface_temp'].min())) /
                (self.lap_stats['avg_tyre_surface_temp'].max() - self.lap_stats['avg_tyre_surface_temp'].min() + 0.001)
        )

        self.lap_stats['tyre_wear_score'] = (
            1 - ((self.lap_stats['avg_tyre_wear'] - self.lap_stats['avg_tyre_wear'].min())) /
                (self.lap_stats['avg_tyre_wear'].max() - self.lap_stats['avg_tyre_wear'].min() + 0.001)
        )

        self.lap_stats['power_efficiency_score'] = (
            1 - ((self.lap_stats['avg_power_efficiency'] - self.lap_stats['avg_power_efficiency'].min())) /
                (self.lap_stats['avg_power_efficiency'].max() - self.lap_stats['avg_power_efficiency'].min() + 0.001)
        )

        self.lap_stats['final_score'] = (
            (0.3 * self.lap_stats['speed_score']) +
            (0.175 * self.lap_stats['consistency_score']) +
            (0.175 * self.lap_stats['tyre_surface_temp_score']) +
            (0.175 * self.lap_stats['tyre_wear_score']) +
            (0.175 * self.lap_stats['power_efficiency_score'])
        )

        top_n = 3

        self.benchmark_laps = self.lap_stats.nlargest(top_n, 'final_score')['lap'].values
        
    def splitTestTrain(self):
        df_benchmark = self.df[self.df['lap'].isin(self.benchmark_laps)].copy()
                
        self.feature_columns = [
            'worldPositionX', 'worldPositionZ', 'lap_progress', 'corner_id',
            
            'speed', 'gear', 'engineRPM', 'engineTemperature',
            
            'avg_diff_tyre_surface_temp', 'avg_diff_tyre_wear',
            
            # 'gForceLateral', 
            # 'gForceVertical', 
            'power_efficiency'
        ]

        self.target_columns = [
            'throttle', 'brake', 'steer'
        ]
        
        X = df_benchmark[self.feature_columns].copy()
        y = df_benchmark[self.target_columns].copy()
        
        X = X.fillna(X.mean())
        y = y.fillna(0)        
                
        return train_test_split(X, y, test_size=0.2, random_state=42)
    
    def normalizedFeatures(self):
        self.scaler = StandardScaler()
        self.X_train_scaled = self.scaler.fit_transform(self.X_train)
        self.X_test_scaled = self.scaler.transform(self.X_test)
        
    def applyRegressor(self):                        
        base_model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42,
            verbose=0
        )
        
        self.model = MultiOutputRegressor(base_model, n_jobs=-1)        
        self.model.fit(self.X_train_scaled, self.y_train)        
        
        self.train_score = self.model.score(self.X_train_scaled, self.y_train)
        self.test_score = self.model.score(self.X_test_scaled, self.y_test)        
        
        y_pred = self.model.predict(self.X_test_scaled)
            
        for i, target in enumerate(self.target_columns):
            mae = mean_absolute_error(self.y_test.iloc[:, i], y_pred[:, i])
            
    def setFeatureImportance(self):
        feature_importance = np.mean([
            estimator.feature_importances_ for estimator in self.model.estimators_
        ], axis=0)

        # Criar dataframe de importâncias
        self.importance_df = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': feature_importance
        }).sort_values('importance', ascending=False)
        
    def saveTrainedModels(self):        
        models_path = f"analisys/models/{self.track}/{self.session}"

        os.makedirs(models_path, exist_ok=True)
        
        joblib.dump(self.model, f"{models_path}/driving_style_model.pkl")        
        
        joblib.dump(self.scaler, f"{models_path}/feature_scaler.pkl")        
        
        config = {
            'feature_columns': self.feature_columns,
            'target_columns': self.target_columns,
            'benchmark_laps': self.benchmark_laps.tolist(),
            'train_score': self.train_score,
            'test_score': self.test_score,
            'feature_importance': self.importance_df.to_dict('records')
        }
        
        with open(f"{models_path}/model_config.json", 'w') as f:
            json.dump(config, f, indent=2)        
        
        self.lap_stats.to_csv(f"{models_path}/lap_statistics.csv", index=False)        