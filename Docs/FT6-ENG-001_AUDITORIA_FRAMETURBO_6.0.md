# DOSSIÊ DE ENGENHARIA, ARQUITETURA E AUDITORIA INDEPENDENTE: FRAMETURBO 6.0

**Documento Oficial:** FT6-ENG-001
**Sistema:** FrameTurbo
**Versão-Alvo:** 6.0
**Base Histórica:** FrameTurbo 5.3.6
**Especificação de Referência:** FrameTurbo 6.0 — Especificação Mestre v1.1
**Status da Auditoria:** Concluída — Arquitetura Avaliada / Implementação 6.0 Não Iniciada
**Data da Emissão:** Outubro de 2024 / Revisão Técnica de Engenharia
**Auditor Independente:** Especialista em Arquitetura de Software Concorrente, Sistemas Distribuídos e Computação Gráfica

---

## SUMÁRIO EXECUTIVO E ESTRUTURAÇÃO DO DOSSIÊ

Este dossiê técnico consolida o parecer formal e exaustivo de auditoria independente de engenharia de software e arquitetura de sistemas para o **FrameTurbo 6.0**. A análise foi conduzida estritamente com base nos princípios de ceticismo técnico, reprodutibilidade, segurança em persistência transacional e preservação inegociável da integridade visual dos artefatos de renderização gerados via Blender 5.2.

O documento organiza-se nos sete entregáveis formais mandatórios:
- **DOCUMENTO A:** Relatório de Auditoria Arquitetural e Análise Crítica
- **DOCUMENTO B:** Arquitetura Recomendada, Contratos Formais e Fronteiras
- **DOCUMENTO C:** Plano Mestre de Implementação e Evolução (Fases 0 a 9)
- **DOCUMENTO D:** Matriz Completa de Riscos Técnicos e Mitigações
- **DOCUMENTO E:** Matriz de Verificação, Validação e Testes Empíricos
- **DOCUMENTO F:** Registro Canônico de Decisões de Arquitetura (ADRs 001 a 005)
- **DOCUMENTO G:** Veredito Final de Engenharia e Recomendações Vinculantes

---

# DOCUMENTO A — RELATÓRIO DE AUDITORIA ARQUITETURAL

## 1. Resumo Executivo da Auditoria

O FrameTurbo é concebido como um orquestrador resiliente e adaptativo para renderização de sequências de animação e frames no Blender 5.2. O objetivo anunciado da versão 6.0 é transcender o modelo histórico de automação monolítica baseado em scripts Python (linhagem 5.x) em direção a uma plataforma modular baseada em microsserviços/processos desacoplados, dotada de inteligência de cena, controle fino de concorrência, recuperação autônoma de desastres e alocação adaptativa de hardware heterogêneo.

A auditoria identificou que, embora a visão conceitual delineada na Especificação Mestre v1.1 seja altamente sofisticada e aponte para mitigações de problemas crônicos da computação gráfica distribuída, a proposta original padece de **superdimensionamento conceitual (overengineering prematuro)**, **premissas otimistas de hardware e drivers que não se sustentam na prática**, e **pontos cegos graves de persistência e concorrência**.

### Classificação Epistemológica dos Artefatos Avaliados:
1. **FATO VERIFICADO:**
   - O ambiente operacional alvo baseia-se em: CPU Intel Xeon E5-2680 v4 (14c/28t, Broadwell-EP, AVX2), 16 GB DDR4 2133 MHz operando em canal único (*Single-channel*), GPU AMD Radeon RX 480/580 (Polaris, 4 GB VRAM GDDR5), Windows 11 Pro 64-bit e Blender 5.2.
   - No Blender 5.2, o motor **Cycles não possui suporte oficial a OpenCL** (removido no Blender 3.0) e **não possui suporte oficial a HIP para a arquitetura Polaris (GFX8)**. Portanto, o suporte oficial a Cycles GPU ou Cycles Híbrido CPU+GPU é inexistente nessa máquina.
   - A configuração de memória RAM em Single-Channel reduz pela metade a largura de banda teórica do barramento de memória (limitando a ~17 GB/s em vez dos ~68 GB/s possíveis em quad-channel no socket LGA2011-v3), o que torna transferências pesadas de geometria e texturas um gargalo severo.

2. **EVIDÊNCIA HISTÓRICA REPORTADA:**
   - A versão 5.3.6 obteve veredito B em auditoria RC1 prévia com 103 verificações PASS, 47 OK e 7 hunks de diff.
   - Persiste documentada a ressalva crítica da **janela de inconsistência entre memória volátil e persistência**, em que falhas de processo resultam em divergência entre arquivos no sistema de arquivos e o estado lógico registrado.

3. **PENDÊNCIA / NÃO VERIFICADO:**
   - O script físico `frameturbo_5.3.6.py` e sua variante `frameturbo_5.3.7_telemetria.py` não constam do repositório ativo no momento desta auditoria. O código-fonte legado é mantido sob status formal de **NÃO VERIFICADO**, impedindo qualquer validação estática de diffs ou reprodutibilidade empírica imediata de seus 103 testes.
   - O comportamento real do plugin BlendLuxCore 2.11.1 (OpenCL) e Radeon ProRender 3.7.0 no Blender 5.2 sobre Windows 11 com drivers Adrenalin modernos para Polaris é **NÃO HOMOLOGADO**.

4. **HIPÓTESE / PROPOSTA:**
   - As alegações de que a renderização híbrida CPU+GPU trará ganhos lineares de desempenho no LuxCore ou ProRender são hipóteses teóricas não demonstradas empiricamente nesta máquina física.
   - Propostas de dynamic hardware balancing baseadas em heurísticas contínuas e predição perceptual de movimento em tela (SSM) constituem conceitos que requerem validação antes de serem admitidos na esteira de produção.

---

## 2. Auditoria da "Janela Crítica Entre Memória e Persistência"

A ressalva identificada na auditoria histórica da versão 5.3.6 é o risco mais severo de todo o sistema: **a dissociação entre o progresso da execução e o registro transacional**.

### Diagnóstico da Falha:
Nos modelos de script anteriores, o estado da tarefa era frequentemente manipulado em variáveis locais do Python (memória volátil). Quando a renderização de um frame era concluída pelo subprocesso do Blender, havia um intervalo de tempo em que:
1. O arquivo PNG/EXR já estava gravado no diretório final de saída.
2. O processo do Blender havia retornado o código de saída 0.
3. Mas a gravação do registro `STATUS = COMPLETED` no banco de dados ainda não havia ocorrido ou foi interrompida (por `SIGKILL`, falta de energia, crash de driver ou exceção de I/O).

Caso o processo caísse nesse milissegundo:
- Ao reiniciar, o orquestrador lia o banco de dados e via a tarefa como `PENDING` ou `IN_PROGRESS`.
- O orquestrador relançava o frame, sobrescrevendo cegamente o arquivo existente e desperdiçando ciclos de hardware.
- Pior: se o processo caísse durante a escrita do arquivo pelo Blender, um arquivo corrompido de 0 bytes ou truncado permanecia no disco, mas futuras checagens simplórias baseadas em `os.path.exists()` consideravam a imagem como pronta.

### Solução Arquitetural Vinculante:
Para erradicar a janela de inconsistência, o FrameTurbo 6.0 deve adotar o princípio de **Fencing Tokens + Escrita em Staging Temporário + Promoção Atômica Condicional**:
1. Nenhum frame é renderizado diretamente no caminho final `outputs/{frame}.png`.
2. A renderização ocorre em um diretório volátil isolado por tentativa: `temp/staging/{job_id}_{attempt_id}_{fencing_token}/output.png`.
3. O status só transita no SQLite dentro de uma transação `BEGIN IMMEDIATE`.
4. A promoção do arquivo temporário para o destino canônico ocorre via `os.replace` (operação atômica em nível de sistema de arquivos NTFS/POSIX) **somente após** a validação estrutural do arquivo e validação do lease no banco.

---

## 3. Avaliação de Módulos: Redundâncias, Ausências e Riscos

| Módulo Proposto | Diagnóstico Crítico | Recomendação da Auditoria |
|---|---|---|
| **DQE (Data Quality Engine)** | Sobreposição de escopo. Tentava avaliar simultaneamente geometria da cena (polígonos, vértices), materiais e predição de tempo. Complexidade geométrica não se correlaciona linearmente com tempo de render (ex: shaders procedurais pesados com 1 único plano vs 1 milhão de polígonos sem material). | **Redefinir como Scene Structural Inspector**. Deve limitar-se a extrair metadados objetivos (contagem de vértices, instâncias, volumetria, resoluções de texturas, luzes ativas) sem emitir estimativas mágicas de custo. |
| **KeyMaster** | Risco de ponto único de falha temporal e confusão semântica. A proposta original misturava "frame esteticamente importante" com "frame computacionalmente representativo". | **Preservar como Âncora Temporal de Validação**. O KeyMaster deve ser puramente um ponto de controle de invariância visual (regressão e pixel delta) e calibração de ruído. Proibido reduzir samples de KeyMasters. |
| **SSM (Screen-Space Motion)** | Redundância e alto custo computacional preliminar. Calcular vetores de movimento e optical flow antes da renderização exige renderizar passes prévios ou pré-visualizações, consumindo o mesmo hardware que se deseja economizar. | **Deslocar para Fase Avançada (Experimental)**. No MVP, utilizar detecção baseada em interpolação de matrizes de transformação de câmera e objetos via Blender Python API (`matrix_world`), que é instantânea e dispensa pré-renderização de pixels. |
| **Scoring vs Confidence** | Risco de pesos arbitrários e falta de interpretabilidade. A criação de equações polinomiais arbitrárias para ranqueamento sem fundamentação estatística gera comportamento imprevisível na fila. | **Fundir em Prioritizer Paramétrico**. O score deve ser decomposto em dimensões ortogonais: Prioridade do Usuário, Risco de Memória e Posição na Sequência (KeyMaster vs Frame Intermediário). Confidence deve ser um indicador de incerteza da medição histórica. |
| **Cache (Structural, Perceptual, Validation)** | Fragmentação excessiva de storage. Ter três mecanismos de cache distintos gera custos de serialização e riscos de invalidação descompassada. | **Unificar sob CacheManager Canônico**. Utilizar um único store indexado por chave SHA-256 composta: `hash(scene_geometry + camera_keyframes + material_hash + ft_version)`. |
| **Dynamic Hardware Balancer (DHB)** | Premissa irrealista para Polaris 4 GB + Xeon Broadwell. Tentar redistribuir tiles em tempo real entre CPU e GPU gera stalls de sincronização via barramento PCIe 3.0 e riscos de estouro de VRAM (*Out-Of-Memory* WDDM crash). | **Substituir por Static Task-Partitioning Balancer**. O balanceamento deve ocorrer a nível de jobs/frames inteiros ou delegação fixa e comprovada de motor, nunca divisão em tempo real de tiles heterogêneos sem suporte do motor. |
| **Output Validator** | **MÓDULO ESSENCIAL AUSENTE NAS BASES LEGADAS**. Historicamente confiava-se no exit code do Blender (0). | **Tornar o Output Validator o Gatekeeper Supremo**. Uma tarefa jamais atinge `COMPLETED` sem passar por inspeção de cabeçalho, decodificação real de bitmap, verificação de canais de cor e integridade SHA-256. |

---

# DOCUMENTO B — ARQUITETURA RECOMENDADA

## 1. Diagrama de Camadas e Fronteiras Arquiteturais

A arquitetura do FrameTurbo 6.0 é rigorosamente desacoplada em seis camadas concêntricas (Hexagonal / Clean Architecture). O núcleo do sistema desconhece os motores de renderização, operando estritamente sobre contratos abstratos.

```
+-----------------------------------------------------------------------+
|                             USER / CLI / API                          |
+-----------------------------------------------------------------------+
                                  |
+-----------------------------------------------------------------------+
| CAMADA 1: CORE ORCHESTRATION & CONTRACTS                             |
|  - Data Contracts (RenderJob, WorkerLease, RenderResult, EffectiveCfg)|
|  - KeyMaster & Sequence Registry                                      |
|  - Prioritizer & Dependency Graph                                     |
+-----------------------------------------------------------------------+
         |                                                 |
+-----------------------------------+   +-------------------------------+
| CAMADA 2: PERSISTENCE & LEASING   |   | CAMADA 3: SCENE PERCEPTION    |
|  - SQLite (WAL Mode, Strict Ty)   |   |  - Headless Scene Inspector   |
|  - Atomic Claims Engine           |   |  - Transform Motion Extractor |
|  - Fencing Token Authority        |   |  - Structural Metadata Cache  |
+-----------------------------------+   +-------------------------------+
         |                                                 |
+-----------------------------------------------------------------------+
| CAMADA 4: SCHEDULER & RESOURCE EVALUATOR                              |
|  - Hardware Resource Evaluator (RAM Budget / VRAM Hard Ceiling)       |
|  - State Machine Driver (PENDING -> CLAIMED -> RUNNING -> ...)        |
|  - Task Queue & Fair Scheduler                                        |
+-----------------------------------------------------------------------+
                                  |
+-----------------------------------------------------------------------+
| CAMADA 5: ISOLATED WORKERS & ENGINE ADAPTERS                          |
|  - Worker Launcher (Subprocess Isolation, Job Sandboxing)             |
|  - Engine Adapters:                                                   |
|      * CyclesCpuAdapter (Baseline Homologado)                         |
|      * LuxCoreAdapter (Experimental / OpenCL Probe)                   |
|      * RadeonProRenderAdapter (Experimental Probe)                    |
|  - Heartbeat & Lease Watchdog                                         |
+-----------------------------------------------------------------------+
                                  |
+-----------------------------------------------------------------------+
| CAMADA 6: AUDIT, TELEMETRY & VALIDATION                               |
|  - Independent Output Validator (Header, Magic Bytes, Pixel Decoding) |
|  - Pixel Delta & Visual Drift Monitor (SSIM, MAE, Perceptual Hash)    |
|  - Telemetry Logger (Disk, Memory, Duration, Exit Code)               |
+-----------------------------------------------------------------------+
```

---

## 2. Contratos Canônicos em Python (Interfaces Tipadas)

Abaixo estão definidos os contratos fundamentais de dados em Python 3.12, imutáveis e protegidos por tipagem estrita (`dataclasses` com `frozen=True` ou validação Pydantic-like).

```python
"""
frameturbo.core.contracts
Contratos formais do FrameTurbo 6.0.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List
import time


class JobStatus(str, Enum):
    PENDING = "PENDING"
    CLAIMED = "CLAIMED"
    RUNNING = "RUNNING"
    STAGING = "STAGING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRY_PENDING = "RETRY_PENDING"
    CANCELLED = "CANCELLED"
    INVALIDATED = "INVALIDATED"


class EngineType(str, Enum):
    CYCLES = "CYCLES"
    LUXCORE = "LUXCORE"
    PRORENDER = "PRORENDER"


class DeviceType(str, Enum):
    CPU = "CPU"
    GPU = "GPU"
    HYBRID = "HYBRID"


@dataclass(frozen=True)
class MemoryBudget:
    max_ram_mb: int
    max_vram_mb: int
    strict_enforcement: bool = True


@dataclass(frozen=True)
class RenderJob:
    job_id: str
    project_id: str
    scene_path: str
    frame_number: int
    is_keymaster: bool
    priority_score: float
    engine_preference: EngineType
    memory_budget: MemoryBudget
    configuration_hash: str
    created_at: float = field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3


@dataclass(frozen=True)
class WorkerLease:
    lease_id: str
    job_id: str
    worker_id: str
    fencing_token: int
    issued_at: float
    expires_at: float
    heartbeat_timeout_sec: float = 30.0


@dataclass(frozen=True)
class EffectiveConfig:
    engine: EngineType
    device: DeviceType
    threads: int
    tile_size: int
    samples: int
    denoiser_enabled: bool
    denoiser_type: str
    output_format: str
    render_timeout_sec: int
    configuration_hash: str


@dataclass(frozen=True)
class ValidationDetails:
    file_exists: bool
    file_size_bytes: int
    image_width: int
    image_height: int
    sha256_checksum: str
    channels: int
    color_depth_bits: int
    is_structurally_valid: bool
    rejection_reason: Optional[str] = None


@dataclass(frozen=True)
class RenderResult:
    job_id: str
    attempt_id: str
    worker_id: str
    fencing_token: int
    exit_code: int
    staging_file_path: str
    final_destination_path: str
    render_duration_sec: float
    peak_ram_mb: float
    peak_vram_mb: float
    validation: ValidationDetails
    completed_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class DQEAnalysisOutput:
    scene_id: str
    total_vertices: int
    total_instances: int
    has_volumetrics: bool
    has_motion_blur: bool
    estimated_vram_mb: int
    complexity_class: str
    analysis_confidence: float
```

---

## 3. Máquina de Estados e Protocolo de Fencing Tokens

O ciclo de vida de uma tarefa obedece a uma máquina de estados finita com persistência imediata e controle rigoroso de concorrência.

```
       [ PENDING ]
            |
    (Atomic Claim via SQL)
            v
       [ CLAIMED ] ---> (Timeout / Worker Dead) ---> [ PENDING ]
            |
     (Launch Process)
            v
       [ RUNNING ] ---> (Process Crash / OOM)  ---> [ RETRY_PENDING ] or [ FAILED ]
            |
  (Blender finishes 0)
            v
       [ STAGING ]
            |
   (Output Validator)
            v
      [ VALIDATING ] -- (Corrupt / Blank / Truncated) -> [ RETRY_PENDING ] / [ FAILED ]
            |
    (Validation PASS & Valid Lease & Atomic os.replace)
            v
      [ COMPLETED ]
```

### Regras Estritas de Transição:
1. `PENDING -> CLAIMED`: Executada via transação SQLite com incremento do `fencing_token`. Se o lease expirar sem heartbeat, o scheduler reseta o estado para `PENDING` e o token é incrementado, invalidando o worker anterior.
2. `CLAIMED -> RUNNING`: Worker confirma inicialização do subprocesso e envia primeiro heartbeat.
3. `RUNNING -> STAGING`: O subprocesso conclui. O arquivo é gerado no diretório de staging:
   `temp/staging/{job_id}_{token}/frame_{frame_number:04d}.png`.
4. `STAGING -> VALIDATING`: O `OutputValidator` examina os bytes do arquivo em staging.
5. `VALIDATING -> COMPLETED`: Transação atômica que:
   - Verifica se o `fencing_token` no banco ainda corresponde ao do Worker.
   - Promove o arquivo via `os.replace(staging_path, final_path)`.
   - Marca `JobStatus.COMPLETED` no SQLite.
6. Se o Worker tentar gravar com um `fencing_token` desatualizado (porque perdeu o lease durante a renderização), o banco rejeita a operação com erro de concorrência (`FencingTokenStaleException`), e o arquivo temporário é sumariamente purgado, prevenindo corrupção de escritas concorrentes.

---

# DOCUMENTO C — PLANO MESTRE DE IMPLEMENTAÇÃO E EVOLUÇÃO

A implementação do FrameTurbo 6.0 é rigorosamente faturada em 10 fases sequenciais (Fase 0 a 9). Nenhuma fase pode iniciar sem que a anterior atinja 100% de seus critérios de saída.

```
+--------+     +--------+     +--------+     +--------+     +--------+
| FASE 0 | --> | FASE 1 | --> | FASE 2 | --> | FASE 3 | --> | FASE 4 |
| Baseline|    |Contratos|    |Percepção|   |KeyMaster|   |Scheduler|
+--------+     +--------+     +--------+     +--------+     +--------+
                                                                |
+--------+     +--------+     +--------+     +--------+         |
| FASE 9 | <-- | FASE 8 | <-- | FASE 7 | <-- | FASE 6 | <------+
|Release |     |Homolog.|     |Hardware|     |Recovery|
+--------+     +--------+     +--------+     +--------+
```

### FASE 0: Auditoria Baseline e Resolução de Pendências
- **Objetivo:** Estabelecer o ambiente de desenvolvimento sob controle de versão, isolando dependências e congelando especificações.
- **Critério de Entrada:** Dossiê FT6-ENG-001 aprovado.
- **Atividades:**
  1. Criação do workspace limpo em `frameturbo/`.
  2. Implementação dos testes de estresse para SQLite sob concorrência e WAL mode no Windows NTFS.
  3. Verificação empírica do ambiente: CLI do Blender 5.2, suporte AVX2 e arquitetura de CPU/RAM.
- **Critério de Saída:** Baseline documentado; suite de persistência executada e aprovada com zero falhas.

### FASE 1: Contratos Formais, Modelos de Dados e Schema SQLite
- **Objetivo:** Construir a base tipada e o banco de dados canônico.
- **Critério de Entrada:** Fase 0 concluída.
- **Atividades:**
  1. Criação dos módulos `frameturbo.core.contracts` e `frameturbo.storage.db`.
  2. Definição do schema relacional no SQLite com modo WAL, foreign keys ativas e índices em `(status, priority_score)`.
  3. Implementação da máquina de estados com transições estritas e exceptions tipadas.
- **Critério de Saída:** 100% dos modelos de dados com testes unitários; transições inválidas rejeitadas por teste.

### FASE 2: Scene Perception & Structural Inspection (DQE Simplificado)
- **Objetivo:** Extração determinística de metadados de cenas `.blend` sem renderização de pixels.
- **Critério de Entrada:** Fase 1 concluída.
- **Atividades:**
  1. Script headless executado pelo Blender (`blender -b scene.blend -P inspect_scene.py`) que extrai contagem de polígonos, tipos de shaders, dimensões de texturas e flags de animação para JSON.
  2. Cálculo de complexidade estrutural normalizada (0.0 a 1.0).
- **Critério de Saída:** Inspeção de cenas de teste executada com extração de metadados em < 2 segundos por cena.

### FASE 3: KeyMaster Engine e Critérios de Ancoragem
- **Objetivo:** Identificação de frames de referência para validação temporal e continuidade.
- **Critério de Entrada:** Fase 2 concluída.
- **Atividades:**
  1. Algoritmo de seleção de KeyMasters baseado em: início/fim de tomadas, mudanças bruscas de câmera (`camera.matrix_world`), e amostragem uniforme mínima (a cada N frames).
  2. Fixação inegociável de amostragem plena para KeyMasters (proibição de degradação de samples).
- **Critério de Saída:** Algoritmo seleciona KeyMasters determinísticos para sequências de teste; persistência de tags no banco.

### FASE 4: Scheduler, Atomic Claims e Isolamento de Workers
- **Objetivo:** Construir o orquestrador de tarefas com suporte a leases e workers em subprocessos.
- **Critério de Entrada:** Fase 3 concluída.
- **Atividades:**
  1. Implementação da rotina de claim atômico via `UPDATE jobs SET status = 'CLAIMED', fencing_token = fencing_token + 1 ...`.
  2. Implementação do `WorkerProcessLauncher` com redirecionamento de logs para `logs/workers/{job_id}.log`.
  3. Heartbeat loop em thread secundária do worker a cada 5 segundos.
- **Critério de Saída:** Teste de concorrência com 10 workers disputando 100 tarefas sem qualquer duplicidade de execução.

### FASE 5: Output Validator & Staging Atômico
- **Objetivo:** Garantir a integridade absoluta dos arquivos de saída.
- **Critério de Entrada:** Fase 4 concluída.
- **Atividades:**
  1. Implementação do `OutputValidator`: validação de cabeçalhos PNG/EXR, resolução, canais de cor e integridade estrutural via `PIL` / `cv2` sem crash.
  2. Implementação do mecanismo de staging atômico via `os.replace`.
- **Critério de Saída:** Teste sintético de injeção de arquivos corrompidos (0 bytes, PNG truncado) rejeitado com status `FAILED`.

### FASE 6: Recovery Manager, Timeouts e Degradação Controlada
- **Objetivo:** Resiliência contra crashes e quedas de processos.
- **Critério de Entrada:** Fase 5 concluída.
- **Atividades:**
  1. Watchdog de leases expirados: devolução automática para a fila com incremento de `retry_count`.
  2. Política de retry exponencial com jitter.
  3. Fallback de motor: se motor experimental falha por OOM, reabre a tarefa com perfil seguro (Cycles CPU).
- **Critério de Saída:** Simulação de encerramento forçado do processo do Blender recuperada com sucesso pelo orquestrador.

### FASE 7: Hardware Manager & Adapters de Renderização
- **Objetivo:** Integração com os motores Blender e orçamentação estrita de memória.
- **Critério de Entrada:** Fase 6 concluída.
- **Atividades:**
  1. Criação do `CyclesCpuAdapter` (motor de baseline).
  2. Criação do `LuxCoreAdapter` (experimental com probes estritas de OpenCL).
  3. Implementação do `MemoryResourceManager` impondo teto absoluto de 12 GB RAM para evitar swapping no Windows.
- **Critério de Saída:** Probes de hardware registram capacidades reais sem travar o processo principal.

### FASE 8: Homologação e Validação Perceptual (Pixel Delta)
- **Objetivo:** Testes ponta a ponta e auditoria de qualidade de imagem.
- **Critério de Entrada:** Fase 7 concluída.
- **Atividades:**
  1. Execução de bateria completa de 250 frames em cena representativa.
  2. Análise de drift visual entre frames consecutivos (SSIM > 0.95 para continuidade).
  3. Auditoria de telemetria completa (latência, pico de memória, falhas de workers).
- **Critério de Saída:** Zero perda de dados; zero corrupção de imagens; conformidade de 100% com o Dossiê.

### FASE 9: Congelamento, Documentação e Release
- **Objetivo:** Publicação da versão homologada FrameTurbo 6.0.
- **Critério de Entrada:** Fase 8 formalmente aprovada.
- **Atividades:**
  1. Geração de pacote limpo de distribuição.
  2. Hash SHA-256 de todos os artefatos de código.
  3. Emissão do relatório final de homologação.
- **Critério de Saída:** Release candidate promovido a versão de produção.

---

# DOCUMENTO D — MATRIZ DE RISCOS TÉCNICOS

| ID | Descrição do Risco | Categoria | Prob. | Imp. | Severidade | Estratégia de Mitigação Obrigatória | Módulo Responsável |
|---|---|---|---|---|---|---|---|
| **RSK-01** | **Condição de Corrida / Execução Duplicada**<br>Dois workers assumem a mesma tarefa após falha transitória de rede ou lentidão no disco. | Concorrência | Média | Alta | **ALTA** | Implementação de `fencing_token` incremental gerado no claim atômico no SQLite. O banco rejeita gravações de workers cujo token seja inferior ao token ativo. | `Scheduler / Persistence` |
| **RSK-02** | **Janela de Inconsistência Memória/Persistência**<br>Processo morre após renderizar arquivo, mas antes de atualizar o status no banco de dados. | Persistência | Alta | Alta | **CRÍTICA** | Protocolo de Staging Atômico: renderizar em `temp/staging/` e somente promover para `outputs/` via `os.replace` dentro da confirmação transacional do banco. | `RecoveryManager / Validator` |
| **RSK-03** | **Crash por Estouro de VRAM (Out-Of-Memory)**<br>Cena excede os 4 GB de VRAM física da Radeon RX 580, gerando crash no WDDM do Windows ou driver reset (TDR). | Hardware | Alta | Alta | **CRÍTICA** | Teto conservador de VRAM alocável para renderização fixado em 2.500 MB (deixando margem para desktop e composição DWM). Bloqueio preventivo de GPU para cenas pesadas; fallback para Cycles CPU. | `MemoryResourceManager / HardwareManager` |
| **RSK-04** | **Incompatibilidade de Motor OpenCL / HIP**<br>Tentativa de executar Cycles GPU via HIP na RX 580 falha no Blender 5.2 (Polaris não suportada). | Compatibilidade | Alta | Alta | **CRÍTICA** | Proibição de ativar HIP para Polaris no Cycles. O adaptador `CyclesCpuAdapter` é declarado a única rota suportada de produção no Cycles. LuxCore OpenCL mantido como experimental isolado. | `BackendAdapters` |
| **RSK-05** | **Gargalo de Banda em RAM Single-Channel**<br>Transferência de malhas densas satura o barramento DDR4 de canal único, travando o sistema operacional. | Hardware | Alta | Média | **ALTA** | Limitação de concorrência a no máximo 1 tarefa pesada por vez. Otimização de exportação de dados via stream binário em memória; redução de geometria desnecessária via DQE. | `Scheduler / DQE` |
| **RSK-06** | **Falsa Aprovação por Código de Saída 0**<br>Blender fecha com código 0, mas gera imagem preta, corrompida ou incompleta por falta de memória ou interrupção. | Qualidade | Alta | Alta | **CRÍTICA** | O código de saída do Blender é tratado como indicador preliminar. A aprovação exige validação de arquivo pelo `OutputValidator` (dimensões, decodificação de imagem, canais válidos). | `OutputValidator` |
| **RSK-07** | **Deriva Visual Silenciosa por Fallback de Motor**<br>Sistema migra frame do LuxCore para Cycles CPU, produzindo diferenças perceptíveis de shaders e iluminação na sequência. | Integridade | Média | Alta | **ALTA** | Proibição estrita de alternar motores dentro da mesma cena de animação sem aprovação explícita do usuário. Fallback ocorre apenas entre dispositivos do mesmo motor (GPU -> CPU). | `RecoveryManager` |
| **RSK-08** | **Lock Contention no Banco de Dados SQLite**<br>Múltiplos workers tentam gravar status simultaneamente no Windows, causando erro de `sqlite3.OperationalError: database is locked`. | Concorrência | Média | Média | **MÉDIA** | Habilitação do modo WAL (`PRAGMA journal_mode=WAL;`), timeout de conexão elevado para 30s (`timeout=30.0`), e centralização de transações no `StorageEngine`. | `StorageEngine` |

---

# DOCUMENTO E — MATRIZ DE TESTES E VERIFICAÇÃO EMPÍRICA

A validação do FrameTurbo 6.0 exige evidências brutas de execução para cada caso de teste. A tabela a seguir especifica os testes obrigatórios.

| Teste ID | Domínio | Objetivo do Teste | Procedimento de Execução | Resultado Esperado | Critério de Aprovação |
|---|---|---|---|---|---|
| **TST-DB-01** | Persistência | Testar concorrência de escritas no SQLite sob modo WAL. | 10 threads concorrentes executando 100 atualizações simultâneas de status no banco com locks aleatórios. | Zero erros de `database is locked`; todas as 1.000 transações persistidas. | Verificação de integridade via `PRAGMA integrity_check;` retornando `ok`. |
| **TST-FNC-01** | Concorrência | Validar a rejeição de workers zumbis através de Fencing Tokens. | Worker 1 assume job com token 1. Força-se timeout do lease. Worker 2 assume job com token 2. Worker 1 tenta promover resultado. | O banco rejeita a escrita do Worker 1 com erro de token obsoleto; staging do Worker 1 é excluído. | Job finalizado exclusivamente com o artefato promovido pelo Worker 2. |
| **TST-VAL-01** | Qualidade | Detecção de arquivos corrompidos e imagens incompletas. | Injetar: (1) arquivo 0 bytes, (2) PNG truncado com cabeçalho danificado, (3) imagem 100% preta de 1x1 pixel. | `OutputValidator` identifica anomalia em todos os 3 casos e rejeita com `ValidationStatus.REJECTED`. | Nenhuma das imagens inválidas atinge o status `COMPLETED`. |
| **TST-HW-01** | Hardware | Medição de estabilidade de VRAM sob Polaris 4 GB. | Executar cena de estresse com alocação progressiva de texturas até 3.800 MB de VRAM no Windows 11. | `MemoryResourceManager` intercepta a alocação ao cruzar 2.500 MB e aborta graciosamente antes do TDR do driver. | O processo Blender é finalizado de forma limpa sem tela azul (BSOD) nem congelamento do SO. |
| **TST-STG-01** | Persistência | Validação de promoção atômica em sistema de arquivos NTFS. | Executar renderização em `temp/staging/`. Simular queda de energia/kill de processo durante a chamada de promoção. | O arquivo de destino nunca é deixado em estado parcialmente escrito; permanece íntegro ou não existe. | Validação SHA-256 do arquivo final corresponde exatamente à digestão computada em staging. |
| **TST-CYC-01** | Motor | Baseline oficial do Cycles no Blender 5.2. | Renderização de frame benchmark usando Cycles CPU (Xeon E5-2680 v4, 28 threads, AVX2). | Renderização concluída com código 0; utilização equilibrada de todas as threads sem throttling térmico. | Imagem renderizada gerada com 100% de integridade estrutural. |
| **TST-LUX-01** | Motor | Probe de compatibilidade do LuxCore OpenCL na RX 580. | Executar probe headless de compilação de kernel OpenCL com BlendLuxCore 2.11.1 no Blender 5.2. | Relatório de probe registra: compilação com sucesso ou erro de driver. Se falhar, registra `UNSUPPORTED`. | Se falhar, o sistema desativa automaticamente a rota LuxCore OpenCL e registra o log técnico. |

---

# DOCUMENTO F — REGISTRO DE DECISÕES DE ARQUITETURA (ADRS)

### ADR-001: Adoção do SQLite em Modo WAL com Fencing Tokens Incrementais
- **Contexto:** Necessidade de gerenciar o estado da fila de renderização com concorrência local entre processos workers sem a complexidade de um broker externo (RabbitMQ/Redis) e eliminando condições de corrida.
- **Alternativas Avaliadas:**
  1. Arquivos JSON/YAML em disco com lockfiles manuais (frágil a crashes e sem transacionalidade).
  2. Servidor Redis local (adiciona dependência de serviço externo não nativo no Windows).
  3. SQLite em modo padrão Rollback Journal (bloqueia leituras durante escritas).
  4. SQLite em modo WAL (Write-Ahead Logging) com `fencing_token`.
- **Decisão:** Adotar SQLite em modo WAL com isolamento de transações imediatas (`BEGIN IMMEDIATE`) e tokens incrementais de proteção de lease (*fencing*).
- **Consequências:** Leituras e escritas concorrem sem bloqueio mútuo; elimina-se o risco de workers atrasados sobrescreverem dados recentes; exige encerramento gracioso para checkpoint do WAL.
- **Status:** **APROVADO E VINCULANTE**.

---

### ADR-002: Desacoplamento Total entre Scheduler e Motores de Renderização via Adapters
- **Contexto:** A arquitetura histórica acoplava comandos de linha de execução do Blender diretamente na lógica de despacho de tarefas, dificultando a inclusão de motores alternativos (LuxCore, Radeon ProRender) e gerando complexidade excessiva no Scheduler.
- **Alternativas Avaliadas:**
  1. Scheduler construindo strings de comando `blender -b -P ...` com blocos `if/else` para cada motor.
  2. Padrão Adapter/Strategy com interface `RenderEngineAdapter` unificada e contratos formais de entrada/saída.
- **Decisão:** Criar a interface abstrata `RenderEngineAdapter`. O Scheduler emite apenas `RenderJob` e `EffectiveConfig`. O Adapter específico é responsável por traduzir isso em parâmetros CLI, scripts auxiliares de inicialização do Blender e parseamento de logs.
- **Consequências:** O Scheduler torna-se 100% agnóstico de motor; novos motores podem ser integrados ou desativados sem qualquer alteração na máquina de estados ou no banco de dados.
- **Status:** **APROVADO E VINCULANTE**.

---

### ADR-003: Orçamentação Estrita e Conservadora de RAM e VRAM para o Hardware Real
- **Contexto:** A máquina de produção conta com hardware modesto e assimétrico: 16 GB de RAM em canal único (Single-Channel) e GPU Radeon RX 580 com apenas 4 GB de VRAM GDDR5 no Windows 11. Estouro de VRAM causa crashes fatais no subsistema WDDM.
- **Alternativas Avaliadas:**
  1. Confiar na paginação automática de memória do Windows (Shared GPU Memory) — causa stalls intoleráveis via PCIe 3.0 e travamento do compositor do Windows.
  2. Alocação dinâmica agressiva assumindo disponibilidade total de 4 GB de VRAM.
  3. Orçamentação estrita: teto de VRAM fixado em 2.500 MB para processos de renderização e 12 GB para memória RAM total do sistema.
- **Decisão:** Fixar tetos conservadores calibráveis: Jobs de GPU são rejeitados ou redirecionados para CPU caso a estimativa de cena ou o consumo em tempo real cruze 2.500 MB de VRAM. A RAM do sistema tem reserva intocável de 4 GB para o SO e processos essenciais.
- **Consequências:** Elimina telas azuis (BSODs) e resets de driver TDR; garante estabilidade do Windows 11; pode forçar cenas muito complexas a utilizarem CPU, priorizando conclusão sobre velocidade.
- **Status:** **APROVADO E VINCULANTE**.

---

### ADR-004: Validação Independente Desacoplada do Exit Code do Blender
- **Contexto:** Processos do Blender frequentemente encerram com código de saída 0 mesmo quando a renderização falhou silenciosamente (ex: cancelamento por script interno, erro de gravação de buffer ou tela preta por câmera sem iluminação).
- **Alternativas Avaliadas:**
  1. Aceitar o arquivo como válido se `process.returncode == 0` e `os.path.exists(file)`.
  2. Validação profunda obrigatória pelo `OutputValidator` independente, inspecionando cabeçalho, decodificação real de imagem e integridade de dimensões.
- **Decisão:** O código de saída 0 é meramente uma condição necessária, mas não suficiente. A tarefa só transita para `VALIDATED` e subsequentemente `COMPLETED` se o `OutputValidator` abrir com sucesso o arquivo de imagem em staging, confirmar as dimensões exatas solicitadas no job e validar que não se trata de arquivo vazio ou corrompido.
- **Consequências:** Erradica imagens defeituosas ou arquivos corrompidos na pasta final de entrega; adiciona custo irrisório de CPU (< 10 ms por frame) para validação de cabeçalho.
- **Status:** **APROVADO E VINCULANTE**.

---

### ADR-005: KeyMaster como Âncora Temporal Invariante de Qualidade
- **Contexto:** Na busca por otimizações de velocidade, versões anteriores consideravam reduzir a amostragem (samples) de frames ao longo da sequência de forma dinâmica.
- **Alternativas Avaliadas:**
  1. Permitir que o orquestrador reduza livremente samples de qualquer frame para atingir metas de tempo.
  2. Isolar frames de referência estruturais (KeyMasters) como âncoras inegociáveis de qualidade plena, proibindo qualquer redução de qualidade visual sobre eles.
- **Decisão:** Os frames designados como KeyMasters são sagrados. Devem ser sempre renderizados na qualidade máxima estipulada pelo projeto. Eles servem de referência para cálculo de ruído e deriva visual (Pixel Delta) para os frames adjacentes.
- **Consequências:** Assegura que a estética do projeto não seja comprometida; garante pontos confiáveis de comparação e regressão na esteira de produção.
- **Status:** **APROVADO E VINCULANTE**.

---

# DOCUMENTO G — VEREDITO FINAL DA AUDITORIA

Com base nas evidências coletadas, na análise estrita da Especificação Mestre v1.1, na confrontação com o hardware físico documentado (Intel Xeon Broadwell-EP, 16 GB Single-Channel, Radeon RX 580 4 GB) e no suporte de software do Blender 5.2:

### Classificação Formal:
## **VEREDITO: B — APROVADO COM RESSALVAS TÉCNICAS E CONDICIONANTES VINCULANTES**

### Justificativa Técnica do Veredito:
A arquitetura do FrameTurbo 6.0 possui méritos excepcionais e direcionamento conceitual correto ao buscar modularidade, controle de concorrência e resiliência de execução. O abandono do modelo de scripts monolíticos é imperativo para a escalabilidade e confiabilidade do orquestrador.

No entanto, o projeto **NÃO PODE** ser aprovado sem ressalvas devido a quatro inconsistências graves que comprometeriam a execução caso fossem implementadas como originalmente concebidas:
1. **Premissas Irreais de GPU no Blender 5.2:** A tentativa de utilizar Cycles via HIP na Radeon RX 580 (Polaris) é tecnicamente inviável sem hacks instáveis não homologados. A arquitetura deve declarar o **Cycles CPU como único baseline estável de produção**, tratando qualquer caminho OpenCL (LuxCore) ou HIP como estritamente experimental.
2. **Gargalo de Hardware Não Mitigado na Especificação Original:** A presença de 16 GB de RAM em canal único (Single-Channel) impõe restrições severas de largura de banda que inviabilizam concorrência simultânea de múltiplos processos Blender pesados.
3. **Persistência de Dados e Risco de Corrupção Concorrente:** A proposta original não formalizava a blindagem contra perdas na janela memória-persistência. A aprovação fica estritamente condicionada à adoção do protocolo de **Fencing Tokens + Escrita em Staging + Promoção Atômica Condicional** (ADR-001 e ADR-004).
4. **Ausência de Artefatos Físicos 5.x no Repositório Ativo:** O código legado da versão 5.3.6 permanece como **NÃO VERIFICADO**, exigindo que a implementação da versão 6.0 seja orientada a testes independentes de contrato e não dependa de heranças não auditadas.

### Condicionantes Obrigatórias para Início da Implementação:
1. **Resolução da Ressalva de Persistência:** Implementar integralmente o módulo `StorageEngine` baseado em SQLite WAL com Fencing Tokens e Staging Atômico antes de qualquer rotina de renderização.
2. **Homologação Experimental de Motores:** Manter os adaptadores de LuxCore e Radeon ProRender atrás de flags experimentais com fallbacks seguros e automáticos para Cycles CPU.
3. **Execução Estrita do Plano de Fases:** Respeitar a ordem das Fases 0 a 9 do Documento C, proibindo a codificação do orquestrador sem a validação prévia dos contratos e dos testes de concorrência.

---
*Fim do Documento FT6-ENG-001 — Dossiê de Engenharia, Arquitetura e Auditoria Independente*
