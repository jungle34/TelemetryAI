import os
import pandas as pd
import numpy as np
import joblib
import json
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from scipy.spatial.distance import euclidean
from scipy.stats import percentileofscore
import warnings
from pathlib import Path
from math import pi

from analisys.GroupData import F125_TelemetryConsolidated

warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

class Mary:
    def __init__(self, track:str, session_training:str, session_analisys:str, lap_to_analize:int):
        self.track = track
        self.session_training = session_training
        self.session_analisys = session_analisys        
        self.lap_to_analize = lap_to_analize
        
        self.model_path = f"analisys/models/{self.track}/{self.session_training}"
        self.feedback_path = f"analisys/models/{self.track}/{self.session_analisys}/Lap_{self.lap_to_analize}"
        os.makedirs(self.feedback_path, exist_ok=True)
        
        basic_consolidated = F125_TelemetryConsolidated(track=self.track, session=self.session_analisys, is_training=False)
        self.parquet_path = basic_consolidated.getBasicConsolidated()
        
        self.df_lap = None
        self.df = None                
        
    def loadModelTrainingFiles(self):
        self.model = joblib.load(f"{self.model_path}/driving_style_model.pkl")
        self.scaler = joblib.load(f"{self.model_path}/feature_scaler.pkl")
        
        with open(f"{self.model_path}/model_config.json", 'r') as f:
            self.config = json.load(f)
        
        self.feature_columns = self.config['feature_columns']
        self.target_columns = self.config['target_columns']
        self.benchmark_laps = self.config['benchmark_laps']
        
        self.df_reference = pd.read_parquet(f"{self.model_path}/benchmark_reference.parquet")
        self.lap_stats = pd.read_csv(f"{self.model_path}/lap_statistics.csv")
        
    def loadLaps(self):
        path_str = f"analisys/sanitazed_data/{self.track}/{self.session_analisys}"
        path = Path(path_str)
        files = [f.name for f in path.glob("*.parquet")]
        if len(files) == 0:
            raise Exception("Aquivo .parquet não foi encontrado")
            
        parquet_path = f"{path_str}/{self.parquet_path['parquet']}"        
        df_new = pd.read_parquet(parquet_path)                

        self.df_lap = df_new[df_new['lap'] == self.lap_to_analize].copy().reset_index(drop=True)
        
    def setInitDataframe(self):
        self.tyre_rolling_range = [5, 10, 15, 20, 25]

        self.tyre_wear_columns = ['tyresWearFL', 'tyresWearFR', 'tyresWearRL', 'tyresWearRR']
        self.tyre_surface_temp_columns = ['tyresSurfaceTemperatureFL', 'tyresSurfaceTemperatureFR', 'tyresSurfaceTemperatureRL', 'tyresSurfaceTemperatureRR']

        self.df = self.df_lap
        self.df = self.df.copy()
        self.df = self.df.sort_values(['lap', 'lapDistance']).reset_index(drop=True)
        
    def setDerivedFeatures(self):
        self.df["avg_tyre_wear"] = self.df[self.tyre_wear_columns].mean(axis=1)

        diff_tyre_wear_columns = []
        for i in self.tyre_rolling_range:
            self.df[f"avg_diff_tyre_wear_{i}"] = self.df["avg_tyre_wear"] - self.df["avg_tyre_wear"].rolling(window=i).mean().fillna(0)
            diff_tyre_wear_columns.append(f"avg_diff_tyre_wear_{i}")    
            
        if len(diff_tyre_wear_columns) > 0:
            self.df["avg_diff_tyre_wear"] = self.df[diff_tyre_wear_columns].mean(axis=1)

        self.df["avg_tyre_surface_temp"] = self.df[self.tyre_surface_temp_columns].mean(axis=1)

        diff_tyre_surface_temp_columns = []
        for i in self.tyre_rolling_range:
            self.df[f"avg_diff_tyre_surface_temp_{i}"] = self.df["avg_tyre_surface_temp"] - self.df["avg_tyre_surface_temp"].rolling(window=i).mean().fillna(0)
            diff_tyre_surface_temp_columns.append(f"avg_diff_tyre_surface_temp_{i}")
            
        if len(diff_tyre_surface_temp_columns) > 0:
            self.df["avg_diff_tyre_surface_temp"] = self.df[diff_tyre_surface_temp_columns].mean(axis=1)    
            
        self.df["is_corner"] = (
            (self.df["steer"].abs() > 0.5) |
            (self.df["gForceLateral"].abs() > 2.0)
        )

        # self.df['avg_tyre_temp_surface'] = self.df[].mean(axis=1)

        self.df["steer_filtered"] = self.df["steer"].where(self.df["steer"].abs() > 0.1, 0)
        self.df["steer_sign"] = np.sign(self.df["steer_filtered"])

        self.df["direction_change"] = self.df["steer_sign"] != self.df["steer_sign"].shift(1)

        self.df["direction_change"] = (
            (self.df["gForceLateral"] * self.df["gForceLateral"].shift(1)) < 0
        )

        self.df["corner_start"] = (
            (self.df["is_corner"]) & (
                (~self.df["is_corner"].shift(1, fill_value=False)) |  # entrou na curva
                (self.df["direction_change"])                         # ou mudou direção (slalom)
            )
        )

        self.df = self.df.drop(columns=["direction_change", "is_corner"] + diff_tyre_surface_temp_columns + diff_tyre_wear_columns)

        self.df["corner_id"] = self.df["corner_start"].cumsum()

        self.df['power_efficiency'] = self.df['speed'] / (self.df['engineRPM'] + 1)

        self.df['lap_progress'] = self.df.groupby('lap').cumcount() / self.df.groupby('lap')['lap'].transform('count')
        
    def processLap(self):
        self.df_lap_processed = self.df.copy()
        # Preparar features
        X_new = self.df_lap_processed[self.feature_columns].copy()
        X_new = X_new.fillna(X_new.mean())

        # Normalizar
        X_new_scaled = self.scaler.transform(X_new)

        # Predizer inputs ideais
        y_pred_ideal = self.model.predict(X_new_scaled)

        # Adicionar ao dataframe
        self.df_lap_processed['throttle_ideal'] = y_pred_ideal[:, 0]
        self.df_lap_processed['brake_ideal'] = y_pred_ideal[:, 1]
        self.df_lap_processed['steer_ideal'] = y_pred_ideal[:, 2]

        # Calcular desvios
        self.df_lap_processed['throttle_diff'] = self.df_lap_processed['throttle'] - self.df_lap_processed['throttle_ideal']
        self.df_lap_processed['brake_diff'] = self.df_lap_processed['brake'] - self.df_lap_processed['brake_ideal']
        self.df_lap_processed['steer_diff'] = self.df_lap_processed['steer'] - self.df_lap_processed['steer_ideal']
        
        self.zone_analysis = self.df_lap_processed.groupby('corner_id').agg({
            'throttle_diff': ['mean', 'std'],
            'brake_diff': ['mean', 'std'],
            'steer_diff': ['mean', 'std'],
            'speed': 'mean',
            'power_efficiency': 'mean',
            'avg_diff_tyre_surface_temp': 'mean',
            'avg_diff_tyre_wear': 'mean',
        }).round(4)
        
    def findCriticalAreas(self, df, threshold_percentile=80):
        df['total_deviation'] = (
            abs(df['throttle_diff']) + 
            abs(df['brake_diff']) + 
            abs(df['steer_diff'])
        )
        
        threshold = np.percentile(df['total_deviation'], threshold_percentile)
        
        # Marcar áreas críticas
        df['is_critical'] = df['total_deviation'] > threshold
        
        # Agrupar áreas críticas consecutivas
        df['critical_group'] = (df['is_critical'] != df['is_critical'].shift()).cumsum()
        
        critical_sections = []
        
        for group_id in df[df['is_critical']]['critical_group'].unique():
            section = df[(df['critical_group'] == group_id) & (df['is_critical'])]
            
            if len(section) == 0:
                continue
            
            critical_sections.append({
                'start_idx': section.index[0],
                'end_idx': section.index[-1],
                'lap_progress': section['lap_progress'].mean(),
                'zone': section['corner_id'].mode()[0] if len(section) > 0 else 'unknown',
                'avg_deviation': section['total_deviation'].mean(),
                'dominant_issue': section[['throttle_diff', 'brake_diff', 'steer_diff']].abs().mean().idxmax().replace('_diff', ''),
                'speed': section['speed'].mean()
            })
        
        return pd.DataFrame(critical_sections).sort_values('avg_deviation', ascending=False)
    
    def generateTextFeedback(self, df, critical_areas, zone_analysis):
        feedback = []
        feedback.append("=" * 60)
        feedback.append(f"📊 RELATÓRIO DE FEEDBACK - VOLTA {df['lap'].iloc[0]}")
        feedback.append("=" * 60)
        feedback.append("")
        
        # Resumo geral
        avg_speed = df['speed'].mean()
        max_speed = df['speed'].max()
        avg_throttle = df['throttle'].mean()
        
        feedback.append("📈 RESUMO GERAL:")
        feedback.append(f"   • Velocidade média: {avg_speed:.1f} km/h")
        feedback.append(f"   • Velocidade máxima: {max_speed:.1f} km/h")
        feedback.append(f"   • Throttle médio: {avg_throttle:.2%}")
        # feedback.append(f"   • Desvio médio do ideal: {df['total_deviation'].mean():.4f}")
        feedback.append("")
        
        # Análise por zona
        feedback.append("🗺️  DESEMPENHO POR ZONA:")
        feedback.append("")
        
        for zone in ['straight', 'braking', 'corner']:
            if zone in zone_analysis.index:
                throttle_dev = zone_analysis.loc[zone, ('throttle_diff', 'mean')]
                brake_dev = zone_analysis.loc[zone, ('brake_diff', 'mean')]
                steer_dev = zone_analysis.loc[zone, ('steer_diff', 'mean')]
                
                feedback.append(f"   📍 {zone.upper()}:")
                
                if abs(throttle_dev) > 0.1:
                    if throttle_dev > 0:
                        feedback.append(f"      ⚠️  Acelerando demais (+{throttle_dev:.2f}) - seja mais conservador")
                    else:
                        feedback.append(f"      ⚠️  Acelerando de menos ({throttle_dev:.2f}) - seja mais agressivo")
                
                if abs(brake_dev) > 0.1:
                    if brake_dev > 0:
                        feedback.append(f"      ⚠️  Freando demais (+{brake_dev:.2f}) - confie mais no carro")
                    else:
                        feedback.append(f"      ⚠️  Freando de menos ({brake_dev:.2f}) - aumente a frenagem")
                
                if abs(steer_dev) > 0.1:
                    if steer_dev > 0:
                        feedback.append(f"      ⚠️  Esterçando demais (+{steer_dev:.2f}) - suavize as curvas")
                    else:
                        feedback.append(f"      ⚠️  Esterçando de menos ({steer_dev:.2f}) - seja mais preciso")
                
                feedback.append("")
        
        # Áreas críticas
        feedback.append("🚨 TOP 3 ÁREAS PARA MELHORAR:")
        feedback.append("")
            
        
        for i, area in critical_areas.head(3).iterrows():
            feedback.append(f"   {i+1}. Setor ~{area['lap_progress']*100:.0f}% da volta")
            feedback.append(f"      • Problema principal: {area['dominant_issue'].upper()}")
            feedback.append(f"      • Desvio: {area['avg_deviation']:.4f}")
            feedback.append(f"      • Velocidade média: {area['speed']:.1f} km/h")
            
            # Dica específica
            if area['dominant_issue'] == 'throttle':
                feedback.append(f"      💡 Dica: Trabalhe a modulação do acelerador nesta zona")
            elif area['dominant_issue'] == 'brake':
                feedback.append(f"      💡 Dica: Ajuste o ponto de frenagem e força aplicada")
            else:
                feedback.append(f"      💡 Dica: Melhore a suavidade da direção")
            
            feedback.append("")
        
        # Pontos fortes
        feedback.append("✅ PONTOS FORTES:")
        feedback.append("")
        
        best_zones = zone_analysis.xs('mean', axis=1, level=1)[['throttle_diff', 'brake_diff', 'steer_diff']].abs().min()
        
        for input_type, value in best_zones.items():
            if value < 0.01:
                feedback.append(f"   • Excelente controle de {input_type.replace('_diff', '')}!")
        
        feedback.append("")
        feedback.append("=" * 60)
        
        return "\n".join(feedback)
    
    def idealInputsChart(self):
        fig, axes = plt.subplots(2, 1, figsize=(16, 4))
        
        axes[0].plot(self.df_lap_processed['lap_progress'], self.df_lap_processed['throttle'], 
                    label='Seu throttle', color='blue', alpha=0.7, linewidth=1.5)
        axes[0].plot(self.df_lap_processed['lap_progress'], self.df_lap_processed['throttle_ideal'], 
                    label='Throttle ideal', color='green', linestyle='--', linewidth=1.5)
        axes[0].fill_between(self.df_lap_processed['lap_progress'], 
                            self.df_lap_processed['throttle'], 
                            self.df_lap_processed['throttle_ideal'], 
                            alpha=0.2, color='red', label='Diferença')
        axes[0].set_ylabel('Throttle')
        axes[0].set_title('Throttle: Real vs Ideal')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # 2. Brake: Real vs Ideal
        axes[1].plot(self.df_lap_processed['lap_progress'], self.df_lap_processed['brake'], 
                    label='Seu brake', color='red', alpha=0.7, linewidth=1.5)
        axes[1].plot(self.df_lap_processed['lap_progress'], self.df_lap_processed['brake_ideal'], 
                    label='Brake ideal', color='orange', linestyle='--', linewidth=1.5)
        axes[1].fill_between(self.df_lap_processed['lap_progress'], 
                            self.df_lap_processed['brake'], 
                            self.df_lap_processed['brake_ideal'], 
                            alpha=0.2, color='purple', label='Diferença')
        axes[1].set_ylabel('Brake')
        axes[1].set_title('Brake: Real vs Ideal')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)  
        
        for ax in axes:
            ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))     

        plt.tight_layout()
        plt.savefig(f"{self.feedback_path}/lap_comparison.png", dpi=150, bbox_inches='tight')
        
    def multiDimenChart(self):        
        for df in [self.df_lap_processed, self.df_reference]:
            df['throttle_smoothness'] = df['throttle'].diff().abs().rolling(5).mean()
            df['brake_smoothness'] = df['brake'].diff().abs().rolling(5).mean()
            df['steer_smoothness'] = df['steer'].diff().abs().rolling(5).mean()

        # Métricas para comparar
        metrics = {
            'Velocidade Média': self.df_lap_processed['speed'].mean() / self.df_reference['speed'].mean(),
            'Consistência Throttle': 1 - (self.df_lap_processed['throttle'].mean() / self.df_reference['throttle'].mean()),
            'Consistência Brake': 1 - (self.df_lap_processed['brake'].mean() / self.df_reference['brake'].mean()),
            'Consistência Steer': 1 - (self.df_lap_processed['steer'].mean() / self.df_reference['steer'].mean()),
            'Temperatura Pneus': 1 - abs(self.df_lap_processed['avg_diff_tyre_surface_temp'].mean() - self.df_reference['avg_diff_tyre_surface_temp'].mean()) / 50,
            'Eficiência Potência': self.df_lap_processed['power_efficiency'].mean() / self.df_reference['power_efficiency'].mean()
        }

        # Limitar valores entre 0 e 1.5 para visualização
        metrics = {k: min(max(v, 0), 1.5) for k, v in metrics.items()}

        categories = list(metrics.keys())
        values = list(metrics.values())
        values += values[:1]  # Fechar o círculo

        angles = [n / float(len(categories)) * 2 * pi for n in range(len(categories))]
        angles += angles[:1]

        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))

        ax.plot(angles, values, 'o-', linewidth=2, label='Sua Performance', color='blue')
        ax.fill(angles, values, alpha=0.25, color='blue')

        # Linha de referência (ideal = 1.0)
        ax.plot(angles, [1.0] * len(angles), '--', linewidth=1, label='Referência Ideal', color='green')

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, size=10)
        ax.set_ylim(0, 1.5)
        ax.set_yticks([0.5, 1.0, 1.5])
        ax.set_yticklabels(['50%', '100%', '150%'])
        ax.grid(True)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))

        plt.title('Comparação Multidimensional vs Benchmark', size=14, pad=20)
        plt.tight_layout()
        plt.savefig(f"{self.feedback_path}/performance_radar.png", dpi=150)
        
    def traceProgressChart(self):
        plt.figure(figsize=(8,8))

        scatter = plt.scatter(
            self.df_lap_processed["worldPositionZ"],
            self.df_lap_processed["worldPositionX"],    
            c=self.df_lap_processed["lap_progress"],
            s=3,
            cmap="tab20c",
        )
        
        plt.xticks([])
        plt.yticks([])
        
        cbar = plt.colorbar(scatter)
        cbar.set_label("Progresso na volta")
        cbar.set_ticks(np.arange(0, 1.01, 0.1))       
        cbar.ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))

        plt.gca().invert_xaxis()
        plt.gca().invert_yaxis()

        plt.title("Progresso da volta no traçado")
        plt.axis("equal")
        plt.savefig(f"{self.feedback_path}/lap_trace.png", dpi=150)
        
    def runAll(self):
        try:
            self.loadModelTrainingFiles()
        except Exception as e:
            raise RuntimeError(e)
        
        try:
            self.loadLaps()
        except Exception as e:
            raise RuntimeError(e)
        
        try:
            self.setInitDataframe()
        except Exception as e:
            raise RuntimeError(e)
        
        try:
            self.setDerivedFeatures()
        except Exception as e:
            raise RuntimeError(e)
        
        try:
            self.processLap()
            self.critical_areas = self.findCriticalAreas(self.df_lap_processed)
        except Exception as e:
            raise RuntimeError(e)
        
        try:
            self.feedback = self.generateTextFeedback(self.df, self.critical_areas, self.zone_analysis)            

            with open(f"{self.feedback_path}/performance_feedback.txt", "w", encoding="utf-8") as f:
                f.write(self.feedback)
        except Exception as e:
            raise RuntimeError(e)
        
        try:
            self.idealInputsChart()            
            self.multiDimenChart()
            self.traceProgressChart()
        except Exception as e:
            raise RuntimeError(e)
        
        return {"success": True}
        
# "Track_3", "2389544128006477957"  
# mary = Mary(track="Track_13", session_training="13955196505268824569", session_analisys="2236946438891290374", lap_to_analize=3)
# mary.runAll()