/**
 * config-pdi.js — endereço do serviço local de Processamento de Imagens.
 *
 * ÚNICO lugar onde a URL da API aparece no site. Trocar a porta é mudar esta linha.
 *
 * Módulo SEPARADO da camada de IA (script/ia/): não importa nada de lá, e a camada de
 * IA não importa nada daqui. O serviço é Python (OpenCV + NumPy) e não usa
 * inteligência artificial.
 */

const CONFIG_PDI = {
  // Serviço iniciado com: cd processamento-imagens && python -m src.api
  urlBase: "http://127.0.0.1:5000",

  // Tempo máximo de espera pela análise. O pipeline leva menos de 1 s por imagem;
  // o limite cobre máquinas lentas e a primeira chamada.
  timeoutMs: 30000,

  // Formatos aceitos pela API. Conferido também no servidor — isto é só conforto.
  extensoesAceitas: [".jpg", ".jpeg", ".png", ".bmp"],

  // Espelha TAMANHO_MAXIMO_BYTES da API (12 MB).
  tamanhoMaximoBytes: 12 * 1024 * 1024,
};
