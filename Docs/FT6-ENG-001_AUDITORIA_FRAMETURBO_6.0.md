# DOSSIÊ DE ENGENHARIA, ARQUITETURA E AUDITORIA INDEPENDENTE: FRAMETURBO 6.0

**Documento Oficial:** FT6-ENG-001
**Sistema:** FrameTurbo
**Versão-Alvo:** 6.0
**Bases Históricas e de Especificação:**
- Base Histórica: FrameTurbo 5.3.6 (e backup 5.3.6 - BK)
- Especificação Mestre v1.0 (Outubro/2026 — Alvo Blender 5.2 / Windows 11 Pro)
- Especificação Mestre v1.1 (Arquitetura Modular)
**Status da Auditoria:** Concluída — Arquitetura e Frente Perceptual Avaliadas / Implementação 6.0 Não Iniciada (Fase 0)
**Data da Emissão:** Outubro de 2024 (Revisão Técnica Expandida: Frente Perceptual SME/MDE/VIE e Gestão de Layers)
**Auditor Independente:** Especialista em Arquitetura de Software Concorrente, Sistemas Distribuídos e Computação Gráfica

---

## SUMÁRIO EXECUTIVO E ESTRUTURAÇÃO DO DOSSIÊ

Este dossiê técnico consolida o parecer formal e exaustivo de auditoria independente de engenharia de software e arquitetura de sistemas para o **FrameTurbo 6.0**. A análise foi conduzida estritamente com base nos princípios de ceticismo técnico, reprodutibilidade, segurança em persistência transacional e preservação inegociável da integridade visual dos artefatos de renderização gerados via Blender 5.2.

Esta revisão técnica incorpora a auditoria profunda da **Especificação Mestre v1.0**, avaliando criticamente os novos componentes da **Frente Perceptual** (SME — Silhouette-Driven Ray Engine, MDE — Multiplane Depth Engine, VIE — Visual Inertia Engine, Perceptual Optimization Coordinator e Key Master) bem como a governança de **View Layers**, isolamento de propriedades no Cycles e hierarquias de execução.

O documento organiza-se nos sete entregáveis formais mandatórios:
- **DOCUMENTO A:** Relatório de Auditoria Arquitetural e Análise Crítica (incluindo Frente Perceptual e Layers)
- **DOCUMENTO B:** Arquitetura Recomendada, Contratos Formais e Fronteiras
- **DOCUMENTO C:** Plano Mestre de Implementação e Evolução (Fases 0 a 9)
- **DOCUMENTO D:** Matriz Completa de Riscos Técnicos e Mitigações
- **DOCUMENTO E:** Matriz de Verificação, Validação e Testes Empíricos (incluindo regressão dos blocos 102–108)
- **DOCUMENTO F:** Registro Canônico de Decisões de Arquitetura (ADRs 001 a 007)
- **DOCUMENTO G:** Veredito Final de Engenharia e Recomendações Vinculantes

---

# DOCUMENTO A — RELATÓRIO DE AUDITORIA ARQUITETURAL

## 1. Resumo Executivo e Análise Crítica da Especificação Mestre v1.0

O FrameTurbo é concebido como um orquestrador local de renderização para o Blender 5.2 sobre Windows 11 Pro. A Especificação Mestre v1.0 estabelece como lema fundamental: *"Primeiro confiabilidade. Depois medição. Em seguida otimização. Por último autonomia."* Este lema alinha-se plenamente com as melhores práticas de engenharia de software.

A arquitetura formaliza a separação entre o Core Orchestrator e os serviços especializados. O Core gerencia o ciclo de vida dos trabalhos; o Blender Adapter orquestra comandos do Blender em background; os Workers renderizam em processos isolados; o SQLite gerencia o estado transacional; o Output Validator assegura a integridade física e lógica dos arquivos gerados; o Recovery Manager trata contingências; a Telemetria monitora o hardware e os tempos; e o Key Master atua como ponto de validação de qualidade temporal e perceptual.

### Classificação Epistemológica dos Artefatos Avaliados (Taxonomia Canônica):
1. **CONFIRMADO (Fato Verificado no Ambiente / Código):**
   - Ambiente operacional alvo: CPU Intel Xeon E5-2680 v4 (14 núcleos físicos / 28 threads, Broadwell-EP, AVX2), 16 GB DDR4 2133 MHz operando em canal único (*Single-channel*), GPU AMD Radeon RX 480/580 (Polaris / GCN 4, 4 GB VRAM GDDR5), Windows 11 Pro 64-bit e Blender 5.2.
   - No Blender 5.2, a documentação oficial e a implementação de backend exigem AMD RDNA1 ou mais recente para aceleração HIP. A arquitetura Polaris (GFX8) não é suportada pelo HIP do Blender 5.2, e o suporte OpenCL no Cycles foi removido no Blender 3.0. Logo, **o Cycles GPU via HIP na RX 580 é BLOQUEADO** e **Cycles CPU é o único baseline estável e homologado**.
   - A configuração de memória RAM em Single-Channel reduz pela metade a largura de banda teórica do barramento de memória (limitando a ~17 GB/s em vez dos ~68 GB/s possíveis em quad-channel no socket LGA2011-v3), o que torna transferências de geometria densa e texturas pesadas um gargalo físico severo.

2. **DOCUMENTADO (Previsto em documentação oficial / histórico):**
   - A versão 5.3.6 obteve veredito B em auditoria RC1 prévia com 103 verificações PASS, 47 OK e 7 hunks de diff.
   - A ressalva crítica da **janela de inconsistência entre memória volátil e persistência** permanece aberta até que seja sanada por implementação comprovada.
   - A API do Blender 5.2 expõe `ViewLayer.samples` como override local de amostragem condicionado à propriedade global da cena de Layer Samples (`Use`, `Bounded` ou `Ignore`). Em contrapartida, controles de Light Paths (máximo de bounces por tipo de raio: diffuse, glossy, transmission, volume) pertencem ao contexto global da Scene (`scene.cycles.max_bounces`), não sendo isolados nativamente por View Layer.

3. **EXPERIMENTAL / HIPÓTESE (Propostas Conceituais Não Homologadas):**
   - Os módulos perceptuais **SME**, **MDE** e **VIE** são conceituais/experimentais. Nenhum possui prova de conceito executada ou homologação de equivalência visual.
   - A viabilidade de reprojeção temporal parcial (VIE) sem artefatos de desoclusão no pipeline do Cycles é uma hipótese que exige validação rigorosa.
   - O comportamento do BlendLuxCore 2.11.1 (OpenCL) e Radeon ProRender 3.7.0 no Blender 5.2 em Windows 11 com drivers Polaris é **EXPERIMENTAL / NÃO HOMOLOGADO**.

4. **BLOQUEADO (Não permitido no MVP):**
   - Uso da RX 580 como backend do Cycles (HIP não suportado na Polaris).
   - Render farm multi-host compartilhando banco SQLite via rede (SMB).
   - Modificações destrutivas e permanentes nos arquivos `.blend` originais.
   - Suposição de controle de bounces por View Layer ou cortes de raios por zona de profundidade no integrador do Cycles.

---

## 2. Auditoria da Frente Perceptual: SME, MDE, VIE e Perceptual Coordinator

A Especificação Mestre v1.0 introduz uma suíte perceptual avançada. A auditoria externa avaliou o escopo, viabilidade e limites de cada componente:

### 2.1 SME — Silhouette-Driven Ray Engine
- **Proposta:** Analisar a relevância de silhuetas, contornos geométricos e regiões de alto contraste visual para direcionar amostragem.
- **Análise Crítica:** O Cycles não expõe uma API pública de controle de densidade de raios por pixel ou por silhueta de objeto durante o path tracing integrativo. Qualquer tentativa de forçar isso internamente no Cycles exigiria compilar um fork customizado do Blender em C++, o que foi expressamente excluído do escopo.
- **Parecer da Auditoria:** O SME deve ser classificado como **EXPERIMENTAL** e atuar exclusivamente em nível de pré-análise e composição (ex: identificação de máscaras de contorno via Cryptomatte / Freestyle pass para guiar passes de denoiser ou composição). Não deve assumir controle do integrador de iluminação.

### 2.2 MDE — Multiplane Depth Engine
- **Proposta:** Analisar profundidade, foco e desfoque de campo (DOF) para identificar oportunidades seguras de LOD (Level of Detail), simplificação de malhas e resolução de texturas em planos desfocados.
- **Análise Crítica:** Cortar bounces de iluminação global por zona de profundidade quebraria a conservação de energia e a física do transporte de luz no Cycles. No entanto, LOD geométrico e redução de mipmaps para objetos distantes ou fora de foco na câmera são práticas consolidadas na computação gráfica.
- **Parecer da Auditoria:** O MDE é **VIÁVEL COMO ANALISADOR DE PRÉ-PROCESSO**, mas **NÃO DEVE ALTERAR BOUNCES DO CYCLES**. O MDE pode recomendar simplificação de malha em memória antes do render apenas no modo `MANUAL` ou `ASSISTED`, sob estrito controle de regressão visual.

### 2.3 VIE — Visual Inertia Engine
- **Proposta:** Investigar reutilização, reprojeção e atualização seletiva de pixels/regiões entre quadros sucessivos, com detecção de desoclusão e validação temporal.
- **Análise Crítica:** Em animações com iluminação dinâmica, sombras em movimento, superfícies reflexivas/refrativas e câmeras móveis, a reprojeção ingênua de pixels produz ghosting severo, descontinuidade temporal e perda de detalhes finos. Além disso, o custo computacional de warp de imagem, cálculo de fluxo óptico e composição pode facilmente anular o ganho de tempo de renderização em uma CPU de 28 threads.
- **Parecer da Auditoria:** O VIE deve ser mantido estritamente em **QUARENTENA EXPERIMENTAL**. Proibido aplicar reprojeção de pixels para substituição de quadros no pipeline de produção. O VIE pode, contudo, fornecer dados para o **Temporal Validator**, ajudando a detectar flickering e anomalias de ruído.

### 2.4 Perceptual Optimization Coordinator & Key Master
- **Perceptual Optimization Coordinator:** Atua como sintetizador de propostas, combinando mapas de saliência do SME, MDE e VIE. **Regra Inegociável:** O coordenador jamais pode aplicar alterações de renderização de forma autônoma sem passar pela política de homologação ou autorização explícita do usuário.
- **Key Master:** Componente vital de qualidade. A auditoria ratifica que o Key Master **NÃO É UM WORKER** e **NÃO SUBSTITUI O OUTPUT VALIDATOR**. O Key Master opera sobre uma amostragem estratégica de quadros (mudanças de plano, início/fim de tomadas, picos de complexidade) para assegurar que não haja deriva visual (*drift*) na sequência. **É terminantemente proibido reduzir a contagem de samples de um Key Master.**

---

## 3. Gestão de View Layers e Hierarquia de Execução

### 3.1 Unidade de Execução no MVP: `FRAME_ORIENTED`
A auditoria aprova a decisão técnica da Especificação v1.0:
- **Modo Padrão no MVP: `FRAME_ORIENTED`**. A tarefa de renderização processa a cena, o quadro e o conjunto explícito de View Layers habilitadas em um único disparo.
- **Motivo Arquitetural:** Renderizar View Layers em processos separados (`LAYER_ORIENTED`) gera overhead catastrófico de reinicialização do Blender, releitura do arquivo `.blend` de 16 GB RAM Single-Channel e recálculo redundante de estruturas BVH (Bounding Volume Hierarchy).
- O modo `LAYER_ORIENTED` permanece como trilha experimental futura para cenas onde a separação em passes isolados compense o overhead de I/O e inicialização.

### 3.2 Isolamento de Propriedades: View Layer vs Scene
Conforme verificado na API do Blender 5.2:
- `ViewLayer.samples`: É um override local de amostragem por layer, condicionado à configuração da cena `scene.cycles.use_layer_samples`.
- Bounces de luz (`scene.cycles.max_bounces`, `diffuse_bounces`, etc.): São propriedades globais da Scene. O `BlenderAdapter` deve rejeitar qualquer perfil que tente impor bounces divergentes por View Layer no mesmo frame.

---

## 4. Auditoria da "Janela Crítica Entre Memória e Persistência"

A persistência do estado no SQLite deve ser protegida contra a janela de inconsistência identificada no FrameTurbo 5.3.6:
1. **Problema:** Morte de processo entre a geração do arquivo pelo Blender e a escrita de `STATUS = COMPLETED` no banco.
2. **Solução Obrigatória:** O protocolo de **Fencing Tokens + Escrita em Staging Temporário + Promoção Atômica Condicional**:
   - O Worker renderiza em: `temp/staging/{job_id}_{attempt}_{token}/frame_{frame:04d}.png`.
   - O `OutputValidator` valida o arquivo em staging (cabeçalho, bytes, resolução, integridade).
   - O Core executa transação SQLite `BEGIN IMMEDIATE`, valida o `fencing_token` ativo e promove atomicamente o arquivo via `os.replace` para `output/final/`.

---

# DOCUMENTO B — ARQUITETURA RECOMENDADA

## 1. Diagrama de Camadas e Fronteiras Arquiteturais

```
+-------------------------------------------------------------------------------+
|                             USER / CLI / INTERFACE                            |
|             Modos: MANUAL (Inspeção) | ASSISTED | AUTO_CERTIFIED              |
+-------------------------------------------------------------------------------+
                                      |
+-------------------------------------------------------------------------------+
| CAMADA 1: CORE ORCHESTRATION & POLICIES                                       |
|  - Lifecycle Controller & State Machine Driver                                |
|  - Canonical Contracts (ProjectManifest, RenderJob, RenderResult, etc.)       |
|  - Execution Authority (Single-Writer Lógico para Persistência)              |
+-------------------------------------------------------------------------------+
         |                                                 |
+-----------------------------------+   +---------------------------------------+
| CAMADA 2: PERSISTENCE & LEASING   |   | CAMADA 3: SCENE PERCEPTION & LAYERS   |
|  - SQLite (WAL Mode, Immediate)   |   |  - Headless SceneAnalyzer & Inspector |
|  - Atomic Claims Engine           |   |  - DependencyGraph & LayerAnalyzer    |
|  - Fencing Token Authority        |   |  - SME / MDE / VIE (Perceptual Suíte) |
|  - Regression Verifier (102-108)  |   |  - Perceptual Optimization Coordinator|
+-----------------------------------+   +---------------------------------------+
         |                                                 |
+-------------------------------------------------------------------------------+
| CAMADA 4: SCHEDULER & RESOURCE EVALUATOR                                      |
|  - Hardware Resource Evaluator (RAM Budget: 12GB max / VRAM: 2.5GB max)       |
|  - Queue Manager & Fair Scheduler (Priority Score + KeyMaster Boost)         |
|  - Execution Modes: FRAME_ORIENTED (MVP) | LAYER_ORIENTED (Experimental)      |
+-------------------------------------------------------------------------------+
                                      |
+-------------------------------------------------------------------------------+
| CAMADA 5: ISOLATED WORKERS & BLENDER ADAPTER                                  |
|  - Subprocess Isolation Launcher (Zero bpy import no Core)                    |
|  - Temporary In-Memory Scene Patching (Preservação estrita do .blend)         |
|  - Adapters:                                                                  |
|      * CyclesCpuAdapter (Baseline Homologado: 8-14 threads calibradas)        |
|      * BlendLuxCoreAdapter (Experimental / OpenCL Probe)                      |
|      * RadeonProRenderAdapter (Experimental Probe)                            |
|  - Heartbeat & Lease Watchdog (30s timeout)                                   |
+-------------------------------------------------------------------------------+
                                      |
+-------------------------------------------------------------------------------+
| CAMADA 6: AUDIT, VALIDATION & TELEMETRY                                       |
|  - Output Validator (Header, Magic Bytes, Dimensions, Channels, SHA-256)      |
|  - Key Master & Temporal Validator (SSIM, Drift Visual, Flicker Detection)    |
|  - Telemetry Engine (Hardware, Latência, Retries, Logs stdout/stderr rotacion)|
|  - Atomic Output Promoter (os.replace via Fencing Token)                      |
+-------------------------------------------------------------------------------+
```

---

## 2. Contratos Canônicos em Python (Interfaces Tipadas)

Abaixo estão os contratos fundamentais de dados expandidos para acomodar a gestão de View Layers e a Frente Perceptual:

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


class ExecutionMode(str, Enum):
    FRAME_ORIENTED = "FRAME_ORIENTED"  # Padrão MVP
    LAYER_ORIENTED = "LAYER_ORIENTED"  # Experimental
    SAMPLE_SUBSET = "SAMPLE_SUBSET"    # Experimental


class OptimizationState(str, Enum):
    NO_CHANGE = "NO_CHANGE"
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPERIMENTAL = "EXPERIMENTAL"


@dataclass(frozen=True)
class MemoryBudget:
    max_ram_mb: int = 12288   # Teto seguro para 16 GB Single-Channel
    max_vram_mb: int = 2500  # Teto seguro para 4 GB RX 580
    strict_enforcement: bool = True


@dataclass(frozen=True)
class LayerRenderProfile:
    layer_id: str
    scene_id: str
    collection_ids: List[str]
    object_ids: List[str]
    passes: List[str]
    aovs: List[str]
    lightgroups: List[str]
    quality_profile_id: str
    samples_override: Optional[int]
    denoise_policy: str
    visibility_policy: Dict[str, bool]
    hardware_policy: str
    validation_policy: str


@dataclass(frozen=True)
class RenderJob:
    job_id: str
    project_id: str
    scene_path: str
    frame_number: int
    view_layer_ids: List[str]
    is_keymaster: bool
    priority_score: float
    execution_mode: ExecutionMode
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
    layer_samples_override: Dict[str, int]
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
    effective_config: EffectiveConfig
    stdout_stderr_log: str
    completed_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class PerceptualOptimizationPlan:
    plan_id: str
    job_id: str
    state: OptimizationState
    sme_silhouette_risk: float   # 0.0 a 1.0 (complexidade de borda)
    mde_depth_complexity: float   # 0.0 a 1.0 (profundidade / DOF)
    vie_temporal_motion: float    # 0.0 a 1.0 (vetores de movimento)
    recommended_samples: int
    confidence_score: float
    justification: str
    fallback_profile: str
    requires_human_approval: bool = True


@dataclass(frozen=True)
class TemporalValidationResult:
    job_id: str
    frame_number: int
    previous_frame_number: int
    ssim_index: float
    mae_diff: float
    flicker_detected: bool
    disocclusion_risk_areas: List[str]
    is_temporally_valid: bool
```

---

# DOCUMENTO C — PLANO MESTRE DE IMPLEMENTAÇÃO E EVOLUÇÃO

A implementação do FrameTurbo 6.0 obedece a 10 fases sequenciais (Fase 0 a 9). Nenhuma fase pode iniciar sem que a anterior tenha seus critérios de saída 100% satisfeitos.

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

### FASE 0: Auditoria Baseline, Resolução de Pendências e Calibração de Hardware
- **Objetivo:** Estabelecer o ambiente de desenvolvimento sob controle de versão, isolando dependências e congelando especificações.
- **Critério de Entrada:** Dossiê FT6-ENG-001 e Especificação Mestre v1.0 aprovados.
- **Atividades:**
  1. Criação do workspace limpo em `frameturbo/`.
  2. Implementação dos testes de estresse para SQLite sob concorrência e WAL mode no Windows NTFS.
  3. Calibração empírica do Xeon E5-2680 v4 no Blender 5.2: medição comparativa de render com 8, 10, 12 e 14 threads para definir número ótimo de threads sem superaquecimento.
  4. Teste formal de regressão dos **blocos 102–108** (cobertura sem gaps nem duplicidades).
- **Critério de Saída:** Baseline documentado; suite de persistência executada e aprovada com zero falhas; threads calibradas.

### FASE 1: Contratos Formais, Modelos de Dados e Schema SQLite
- **Objetivo:** Construir a base tipada e o banco de dados canônico.
- **Critério de Entrada:** Fase 0 concluída.
- **Atividades:**
  1. Implementação dos contratos canônicos em `frameturbo/core/contracts.py`.
  2. Definição do schema relacional no SQLite com modo WAL, foreign keys ativas e índices em `(status, priority_score)`.
  3. Implementação da máquina de estados com transições estritas e exceptions tipadas.
- **Critério de Saída:** 100% dos modelos de dados com testes unitários; transições inválidas rejeitadas por teste.

### FASE 2: Scene Perception & Dependency Graph
- **Objetivo:** Extração determinística de metadados de cenas `.blend` sem renderização de pixels.
- **Critério de Entrada:** Fase 1 concluída.
- **Atividades:**
  1. Script headless executado pelo Blender (`blender -b scene.blend -P inspect_scene.py`) que extrai contagem de polígonos, tipos de shaders, dimensões de texturas, coleções e View Layers.
  2. Implementação do `DependencyGraph` identificando relações entre câmeras, luzes, modifiers e passes.
- **Critério de Saída:** Inspeção de cenas de teste executada com extração de metadados em < 2 segundos por cena.

### FASE 3: KeyMaster Engine, Critérios de Ancoragem e Suíte Perceptual Experimental
- **Objetivo:** Identificação de frames de referência para validação temporal e isolamento de protótipos de SME/MDE/VIE.
- **Critério de Entrada:** Fase 2 concluída.
- **Atividades:**
  1. Algoritmo de seleção de KeyMasters baseado em: início/fim de tomadas, mudanças bruscas de câmera (`camera.matrix_world`), e amostragem uniforme mínima (a cada N frames).
  2. Fixação inegociável de amostragem plena para KeyMasters (proibição de degradação de samples).
  3. Criação do arcabouço experimental para SME/MDE/VIE em modo puramente passivo de análise (sem interferência em render).
- **Critério de Saída:** Algoritmo seleciona KeyMasters determinísticos; tags gravadas no banco; testes unitários de análise passiva aprovados.

### FASE 4: Scheduler, Atomic Claims e Isolamento de Workers
- **Objetivo:** Construir o orquestrador de tarefas com suporte a leases e workers em subprocessos.
- **Critério de Entrada:** Fase 3 concluída.
- **Atividades:**
  1. Implementação da rotina de claim atômico via `UPDATE jobs SET status = 'CLAIMED', fencing_token = fencing_token + 1 ...`.
  2. Implementação do `WorkerProcessLauncher` com modo `FRAME_ORIENTED` e redirecionamento de logs para `logs/workers/{job_id}.log`.
  3. Heartbeat loop em thread secundária do worker a cada 5 segundos.
- **Critério de Saída:** Teste de concorrência com 10 workers disputando 100 tarefas sem qualquer duplicidade de execução.

### FASE 5: Output Validator & Staging Atômico
- **Objetivo:** Garantir a integridade absoluta dos arquivos de saída.
- **Critério de Entrada:** Fase 4 concluída.
- **Atividades:**
  1. Implementação do `OutputValidator`: validação de cabeçalhos PNG/EXR, resolução, canais de cor e integridade estrutural sem crash.
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

### FASE 8: Homologação e Validação Perceptual (Pixel Delta & Temporal)
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
| **RSK-08** | **Artefatos Temporais por Reprojeção Agressiva (VIE)**<br>Tentativa de reutilizar pixels entre quadros gera desoclusões corrompidas e ghosting. | Qualidade Visual | Alta | Alta | **CRÍTICA** | Quarentena do módulo VIE: desativar substituição de pixels no pipeline principal. O VIE deve ser restrito a instrumento de análise e validação temporal. | `VIE / TemporalValidator` |
| **RSK-09** | **Conflito de Bounces Globais entre View Layers**<br>Tentativa de setar bounces de iluminação diferentes por View Layer gera sobrescrita imprevisível no contexto da Scene. | Arquitetura | Alta | Média | **ALTA** | Proibição de overrides de bounces por View Layer. Bounces permanecem estritamente no escopo da Scene (`scene.cycles.max_bounces`), permitindo apenas `ViewLayer.samples`. | `BlenderAdapter / LayerManager` |

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
| **TST-CYC-01** | Motor | Baseline oficial do Cycles no Blender 5.2. | Renderização de frame benchmark usando Cycles CPU (Xeon E5-2680 v4, calibrando 8, 10, 12 e 14 threads, AVX2). | Renderização concluída com código 0; identificação do sweet spot de threads sem saturação térmica. | Imagem renderizada gerada com 100% de integridade estrutural. |
| **TST-REG-102** | Integridade | Regressão histórica dos blocos 102–108. | Despachar sequência de 200 frames com injeção de falhas aleatórias de processo e timeouts forçados. | Cobertura exata do intervalo [102, 108] sem lacunas, sem duplicações e sem blocos sobrepostos. | Zero frames ausentes; zero tarefas órfãs; integridade de sequência 100%. |
| **TST-PERC-01** | Perceptual | Quarentena do módulo VIE (detecção de ghosting). | Simular interpolação/reprojeção de frame com objeto de alto contraste em movimento rápido. | `TemporalValidator` acusa falha de descontinuidade (`disocclusion_risk = True`) e força render completo. | O sistema impede a promoção de quadros com artefatos de interpolação. |

---

# DOCUMENTO F — REGISTRO DE DECISÕES DE ARQUITETURA (ADRS)

### ADR-001: Adoção do SQLite em Modo WAL com Fencing Tokens Incrementais
- **Contexto:** Necessidade de gerenciar o estado da fila de renderização com concorrência local entre processos workers sem a complexidade de um broker externo (RabbitMQ/Redis) e eliminando condições de corrida.
- **Decisão:** Adotar SQLite em modo WAL com isolamento de transações imediatas (`BEGIN IMMEDIATE`) e tokens incrementais de proteção de lease (*fencing*).
- **Status:** **APROVADO E VINCULANTE**.

### ADR-002: Desacoplamento Total entre Scheduler e Motores de Renderização via Adapters
- **Contexto:** A arquitetura histórica acoplava comandos de linha de execução do Blender diretamente na lógica de despacho de tarefas.
- **Decisão:** Criar a interface abstrata `RenderEngineAdapter`. O Scheduler emite apenas `RenderJob` e `EffectiveConfig`. O Adapter específico traduz para parâmetros CLI.
- **Status:** **APROVADO E VINCULANTE**.

### ADR-003: Orçamentação Estrita e Conservadora de RAM e VRAM para o Hardware Real
- **Contexto:** A máquina conta com 16 GB RAM Single-Channel e GPU Radeon RX 580 com 4 GB de VRAM GDDR5 no Windows 11.
- **Decisão:** Fixar tetos conservadores: Jobs de GPU são redirecionados para CPU caso excedam 2.500 MB de VRAM. A RAM do sistema tem reserva intocável de 4 GB para o SO.
- **Status:** **APROVADO E VINCULANTE**.

### ADR-004: Validação Independente Desacoplada do Exit Code do Blender
- **Contexto:** Processos do Blender frequentemente encerram com código de saída 0 mesmo quando a renderização falhou silenciosamente.
- **Decisão:** O código de saída 0 é meramente uma condição necessária, mas não suficiente. A tarefa só transita para `VALIDATED` e `COMPLETED` se o `OutputValidator` abrir com sucesso o arquivo de imagem em staging e validar suas dimensões e canais.
- **Status:** **APROVADO E VINCULANTE**.

### ADR-005: KeyMaster como Âncora Temporal Invariante de Qualidade
- **Contexto:** Na busca por otimizações, versões anteriores consideravam reduzir a amostragem de frames ao longo da sequência de forma dinâmica.
- **Decisão:** Os frames designados como KeyMasters são sagrados. Devem ser sempre renderizados na qualidade máxima estipulada pelo projeto, servindo de âncora de calibração para o Pixel Delta e validação temporal.
- **Status:** **APROVADO E VINCULANTE**.

### ADR-006: Escopo Estrito de Bounces de Cena vs ViewLayer Overrides no Cycles
- **Contexto:** Propostas conceituais sugeriram otimizar caminhos de luz (Light Paths / bounces) individualmente por View Layer.
- **Decisão:** No Blender 5.2, os parâmetros de bounces pertencem estritamente à Scene (`scene.cycles.max_bounces`). O FrameTurbo só permite override por View Layer em `ViewLayer.samples` (quando a política global da cena permitir). Proíbe-se qualquer tentativa de isolamento artificial de bounces por layer na mesma cena.
- **Status:** **APROVADO E VINCULANTE**.

### ADR-007: Quarentena e Classificação Experimental Estrita para a Frente Perceptual (SME/MDE/VIE)
- **Contexto:** A inclusão dos motores perceptuais SME, MDE e VIE na Especificação v1.0 promete ganhos teóricos, mas carece de validação empírica e risco de degradação estética.
- **Decisão:** Todos os três motores são categorizados formalmente como **EXPERIMENTAL**. Fica proibida a substituição autônoma de pixels ou alteração de bounces baseada em predições perceptuais no pipeline de produção. O Perceptual Optimization Coordinator opera exclusivamente sob modo `MANUAL` ou `ASSISTED` com aprovação humana explícita.
- **Status:** **APROVADO E VINCULANTE**.

---

# DOCUMENTO G — VEREDITO FINAL DA AUDITORIA

Com base nas evidências consolidadas, na Especificação Mestre v1.0, na confrontação com o hardware físico documentado (Intel Xeon Broadwell-EP, 16 GB Single-Channel, Radeon RX 580 4 GB) e no suporte de software do Blender 5.2:

### Classificação Formal:
## **VEREDITO: B — APROVADO COM RESSALVAS TÉCNICAS E CONDICIONANTES VINCULANTES**

### Justificativa Técnica do Veredito:
A Especificação Mestre v1.0 do FrameTurbo 6.0 demonstra excelente maturidade metodológica ao instituir o lema *"Primeiro confiabilidade. Depois medição. Em seguida otimização. Por último autonomia."* A separação entre Core, Workers isolados, SQLite e Output Validator resolve os vícios estruturais das versões de script 5.x.

Entretanto, o veredito permanece **B (Aprovado com Ressalvas)** devido aos seguintes fatores impeditivos de aprovação irrestrita:
1. **Frente Perceptual (SME/MDE/VIE) ainda puramente teórica:** As propostas de direcionamento de raios e reprojeção temporal esbarram nos limites do integrador do Cycles e oferecem risco crítico de degradação estética. Devem permanecer isoladas em quarentena experimental.
2. **Polaris / HIP Inviável no Blender 5.2:** O baseline exclusivo de produção para este hardware deve ser mantido como Cycles CPU.
3. **Persistência e Concorrência:** A aprovação vincula-se à implementação do protocolo de Fencing Tokens e Staging Atômico para liquidar em definitivo a ressalva da janela entre memória e persistência.
4. **Regressão dos Blocos 102–108:** A validação final de entrega só ocorrerá após a execução bem-sucedida do teste `TST-REG-102` com 100% de integridade comprovada.

---
*Fim do Documento FT6-ENG-001 — Dossiê de Engenharia, Arquitetura e Auditoria Independente*
