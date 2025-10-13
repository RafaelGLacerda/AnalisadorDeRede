from flask import Flask, send_file, Response
import time
import json
import random 
import os 
from math import floor 

# Configuração para encontrar index.html na mesma pasta
app = Flask(__name__, template_folder='.')

# --- Funções Auxiliares ---

def formatar_sse(data: dict) -> str:
    """Formata um dicionário de dados em uma string Server-Sent Event."""
    json_data = json.dumps(data)
    # Formato SSE: 'data: [JSON]\n\n'
    return f"data: {json_data}\n\n"

def simular_teste_velocidade():
    """Função para simular resultados realistas de um teste de velocidade."""
    
    # Valores de referência realistas
    BASE_DOWNLOAD = 500.0  # Mbps
    BASE_UPLOAD = 100.0    # Mbps
    BASE_PING = 6.0        # ms

    # Adiciona um pequeno ruído para simular variação
    ping = BASE_PING + random.uniform(-1.0, 1.0)
    download_mbps = BASE_DOWNLOAD + random.uniform(-50.0, 50.0)
    upload_mbps = BASE_UPLOAD + random.uniform(-10.0, 10.0)
    
    return {
        # Fixando uma única 'amostra' para o teste de 10 segundos
        'ping': round(max(1.0, ping), 2),
        'download': round(max(0.0, download_mbps), 2),
        'upload': round(max(0.0, upload_mbps), 2)
    }

# --- Rotas do Flask ---

@app.route('/')
def index():
    """Servir o arquivo HTML principal."""
    try:
        # Busca index.html no diretório de execução (PING/)
        return send_file('index.html') 
    except FileNotFoundError:
        return "Erro 404: O arquivo 'index.html' não foi encontrado.", 404


@app.route('/api/teste-stream', methods=['GET'])
def teste_stream():
    """Endpoint que usa SSE para enviar medições e progresso em tempo real."""

    def gerador_eventos_teste():
        TEMPO_TOTAL_MONITORAMENTO = 10.0 # segundos (100% da barra)
        INTERVALO_SLEEP = 0.5 # Intervalo de atualização da barra de progresso
        
        amostra_id = 0
        tempo_inicio = time.time()
        
        # Inicializa as médias para o caso de falha imediata
        media_download = 0.0
        media_upload = 0.0
        media_ping = 0.0
        
        # O teste é simulado UMA VEZ para obter os valores de referência
        try:
            print("Simulando teste de velocidade...")
            resultado_teste_completo = simular_teste_velocidade()
            
            media_download = resultado_teste_completo['download']
            media_upload = resultado_teste_completo['upload']
            media_ping = resultado_teste_completo['ping']
            amostra_id = 1
            
            # Envia a AMOSTRA COMPLETA
            yield formatar_sse({
                'tipo': 'amostra',
                'id': amostra_id,
                'ping': media_ping,
                'download': media_download,
                'upload': media_upload
            })
            
        except Exception as e:
            # Em caso de erro na simulação (improvável), ainda envia o erro
            print(f"ERRO na simulação: {e}")
            yield formatar_sse({'tipo': 'erro', 'mensagem': f'Falha na simulação: {str(e)}'})
            # Se o teste inicial falhar, encerra o gerador
            yield formatar_sse({'tipo': 'fim', 'total_amostras': 0, 'media_ping': 0, 'media_download': 0, 'media_upload': 0})
            return
            
        # LOOP DE ATUALIZAÇÃO DA BARRA DE PROGRESSO (10 SEGUNDOS)
        while time.time() - tempo_inicio < TEMPO_TOTAL_MONITORAMENTO:
            tempo_decorrido = time.time() - tempo_inicio
            progresso_percentual = floor((tempo_decorrido / TEMPO_TOTAL_MONITORAMENTO) * 100)
            
            # Garante que o progresso não passe de 99% antes do fim
            progresso_percentual = min(progresso_percentual, 99)
            
            # Envia o evento de progresso
            yield formatar_sse({
                'tipo': 'progresso',
                'porcentagem': progresso_percentual
                # Os valores de download/upload/ping não precisam ser enviados, 
                # pois o front-end simula a oscilação sobre o resultado fixo (media_download)
            })
            
            time.sleep(INTERVALO_SLEEP)
        
        # 5. Envia o sinal de FIM (100% e resultado final)
        yield formatar_sse({'tipo': 'fim', 'total_amostras': amostra_id, 
                            'media_ping': media_ping,
                            'media_download': media_download,
                            'media_upload': media_upload})
        
    # Retorna uma Response com o mimetype correto para SSE
    return Response(gerador_eventos_teste(), mimetype='text/event-stream')

if __name__ == '__main__':
    print("Servidor Flask rodando em http://127.0.0.1:5000")
    print("Acesse a URL para iniciar: http://127.0.0.1:5000")
    app.run(debug=True, threaded=False)