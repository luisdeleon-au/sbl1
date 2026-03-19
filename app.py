"""
SBL Scenario Designer — Professor De León Workshop
Flask app with Anthropic API for interactive scenario-based learning design.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

# Load .env from the same directory as app.py
load_dotenv(Path(__file__).resolve().parent / ".env")

app = Flask(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

# ──────────────────────────────────────────────
# Prompt Frameworks
# ──────────────────────────────────────────────

def build_scenario_architect_prompt(discipline, topic, level, complexity, scenario_type):
    """Framework 1: SBL Scenario Architect"""
    return f"""# ROL
Eres un diseñador instruccional experto en Aprendizaje Basado en Escenarios (ABE/SBL). 
Tu especialidad es crear experiencias de aprendizaje inmersivas que sitúan al estudiante 
en situaciones realistas donde debe aplicar conocimientos, tomar decisiones y enfrentar consecuencias.

# CONTEXTO DISCIPLINAR
- Disciplina: {discipline}
- Tema específico: {topic}

# PERFIL DEL ESTUDIANTE
- Nivel educativo: {level}
- Conocimientos previos: El estudiante tiene fundamentos básicos en la disciplina pero 
  necesita desarrollar pensamiento crítico y capacidad de toma de decisiones.

# ESTRUCTURA DEL ESCENARIO
- Tipo de escenario: {scenario_type}
- Complejidad: {complexity}
- Puntos de decisión: 3 momentos clave donde el estudiante debe elegir

# INSTRUCCIONES DE GENERACIÓN
Genera un escenario de aprendizaje completo en español con la siguiente estructura JSON:

{{
  "titulo": "Título impactante del escenario",
  "personaje": {{
    "nombre": "Nombre del protagonista",
    "rol": "Rol profesional",
    "contexto": "Breve descripción de quién es y su situación"
  }},
  "ambientacion": "Descripción vívida del entorno (2-3 oraciones)",
  "situacion_inicial": "La situación que enfrenta el personaje (3-4 oraciones)",
  "objetivo_aprendizaje": "¿Qué debe aprender el estudiante al completar este escenario?",
  "decisiones": [
    {{
      "momento": 1,
      "contexto": "Qué está pasando en este momento (2-3 oraciones)",
      "pregunta": "La pregunta/dilema que enfrenta",
      "opciones": [
        {{
          "id": "A",
          "texto": "Opción A",
          "consecuencia": "Qué pasa si elige esto (2-3 oraciones)",
          "es_optima": true/false,
          "feedback_pedagogico": "Por qué esta opción es buena/mala y qué enseña"
        }},
        {{
          "id": "B",
          "texto": "Opción B",
          "consecuencia": "...",
          "es_optima": true/false,
          "feedback_pedagogico": "..."
        }},
        {{
          "id": "C",
          "texto": "Opción C",
          "consecuencia": "...",
          "es_optima": true/false,
          "feedback_pedagogico": "..."
        }}
      ]
    }}
  ],
  "reflexion_final": "Preguntas de reflexión para después del escenario",
  "competencias_desarrolladas": ["competencia 1", "competencia 2", "competencia 3"]
}}

IMPORTANTE: Responde SOLO con el JSON, sin texto adicional ni bloques de código."""


def build_refine_prompt(scenario_json, instruction):
    """Framework 2 variant: Refine an existing scenario"""
    return f"""Tienes el siguiente escenario de aprendizaje basado en escenarios (ABE):

{json.dumps(scenario_json, ensure_ascii=False, indent=2)}

# INSTRUCCIÓN DE REFINAMIENTO
{instruction}

Genera el escenario COMPLETO modificado manteniendo la misma estructura JSON exacta.
Responde SOLO con el JSON actualizado, sin texto adicional ni bloques de código."""


def build_play_prompt(scenario_json, decision_index, choice_id, history):
    """Generate immersive narrative for playing through the scenario"""
    decision = scenario_json["decisiones"][decision_index]
    chosen = next((o for o in decision["opciones"] if o["id"] == choice_id), None)
    
    history_text = ""
    if history:
        history_text = "Decisiones previas del jugador:\n"
        for h in history:
            history_text += f"- Momento {h['momento']}: Eligió {h['opcion']} → {h['resultado']}\n"

    return f"""Eres el narrador de un escenario interactivo de aprendizaje.

# ESCENARIO
Título: {scenario_json['titulo']}
Personaje: {scenario_json['personaje']['nombre']}, {scenario_json['personaje']['rol']}
Ambientación: {scenario_json['ambientacion']}

{history_text}

# DECISIÓN ACTUAL (Momento {decision_index + 1})
Contexto: {decision['contexto']}
Pregunta: {decision['pregunta']}
El estudiante eligió: "{chosen['texto']}"

# INSTRUCCIONES
Genera una respuesta narrativa inmersiva en español como JSON:

{{
  "narrativa": "Descripción vívida y cinematográfica de lo que sucede tras la decisión (4-6 oraciones). Hazlo emocional, sensorial, que el estudiante SIENTA las consecuencias.",
  "impacto": "{chosen['consecuencia']}",
  "leccion": "{chosen['feedback_pedagogico']}",
  "emocion": "una palabra que describe la emoción dominante (ej: tensión, alivio, urgencia, esperanza)",
  "indicador_progreso": "¿Cómo va el protagonista? Breve descripción"
}}

Responde SOLO con el JSON, sin texto adicional ni bloques de código."""


# ──────────────────────────────────────────────
# API Helper
# ──────────────────────────────────────────────

def call_claude(prompt, system=""):
    """Call Anthropic API and return parsed response."""
    import urllib.request
    
    if not ANTHROPIC_API_KEY:
        return {"error": "API key no configurada. Configura ANTHROPIC_API_KEY."}
    
    messages = [{"role": "user", "content": prompt}]
    body = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 4096,
        "messages": messages,
    }
    if system:
        body["system"] = system
    
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            text = ""
            for block in result.get("content", []):
                if block.get("type") == "text":
                    text += block["text"]
            
            # Clean and parse JSON
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
            
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"raw_text": text, "error": "No se pudo parsear la respuesta como JSON"}
    except Exception as e:
        return {"error": str(e)}


def build_copyable_prompt(discipline, topic, level, complexity, scenario_type):
    """Generate a clean, human-readable prompt that students can copy and use in any AI tool."""
    return f"""# ROL
Eres un diseñador instruccional experto en Aprendizaje Basado en Escenarios (ABE/SBL). Tu especialidad es crear experiencias de aprendizaje inmersivas que sitúan al estudiante en situaciones realistas donde debe aplicar conocimientos, tomar decisiones y enfrentar consecuencias.

# CONTEXTO DISCIPLINAR
- Disciplina: {discipline}
- Tema específico: {topic}

# PERFIL DEL ESTUDIANTE
- Nivel educativo: {level}
- Conocimientos previos: El estudiante tiene fundamentos básicos en la disciplina pero necesita desarrollar pensamiento crítico y capacidad de toma de decisiones.

# ESTRUCTURA DEL ESCENARIO
- Tipo de escenario: {scenario_type}
- Complejidad: {complexity}
- Puntos de decisión: 3 momentos clave donde el estudiante debe elegir

# INSTRUCCIONES
Genera un escenario de aprendizaje completo en español que incluya:

1. TÍTULO: Un título impactante para el escenario
2. PERSONAJE: Nombre, rol profesional, y contexto del protagonista
3. AMBIENTACIÓN: Descripción vívida del entorno (2-3 oraciones)
4. SITUACIÓN INICIAL: La situación que enfrenta el personaje (3-4 oraciones)
5. OBJETIVO DE APRENDIZAJE: ¿Qué debe aprender el estudiante?
6. DECISIONES: 3 momentos de decisión, cada uno con:
   - Contexto de lo que está pasando
   - Pregunta/dilema que enfrenta
   - 3 opciones (A, B, C) con consecuencias y feedback pedagógico
7. REFLEXIÓN FINAL: Preguntas de reflexión para después del escenario
8. COMPETENCIAS DESARROLLADAS: Lista de competencias que se practican"""


def build_copyable_refine_prompt(instruction):
    """Generate a copyable refine prompt."""
    return f"""Toma el escenario de aprendizaje que acabamos de crear y aplica la siguiente modificación:

{instruction}

Mantén la misma estructura completa (personaje, ambientación, situación, decisiones con opciones y consecuencias, reflexión) pero incorpora los cambios solicitados. Genera el escenario completo modificado."""


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/generate", methods=["POST"])
def generate_scenario():
    """Phase 1: Generate a new scenario"""
    data = request.json
    discipline = data.get("discipline", "Educación")
    topic = data.get("topic", "Ética profesional")
    level = data.get("level", "Pregrado")
    complexity = data.get("complexity", "Intermedia")
    scenario_type = data.get("scenario_type", "Ramificado")
    
    prompt = build_scenario_architect_prompt(
        discipline=discipline, topic=topic, level=level,
        complexity=complexity, scenario_type=scenario_type,
    )
    copyable = build_copyable_prompt(
        discipline=discipline, topic=topic, level=level,
        complexity=complexity, scenario_type=scenario_type,
    )
    
    result = call_claude(prompt)
    
    if "error" not in result:
        result["_prompt"] = copyable
    
    return jsonify(result)


@app.route("/api/refine", methods=["POST"])
def refine_scenario():
    """Phase 2: Refine existing scenario"""
    data = request.json
    scenario = data.get("scenario")
    instruction = data.get("instruction", "")
    
    if not scenario:
        return jsonify({"error": "No hay escenario para refinar"}), 400
    
    prompt = build_refine_prompt(scenario, instruction)
    copyable = build_copyable_refine_prompt(instruction)
    result = call_claude(prompt)
    
    if "error" not in result:
        result["_prompt"] = copyable
    
    return jsonify(result)


@app.route("/api/play", methods=["POST"])
def play_scenario():
    """Phase 3: Play through a scenario decision"""
    data = request.json
    scenario = data.get("scenario")
    decision_index = data.get("decision_index", 0)
    choice_id = data.get("choice_id", "A")
    history = data.get("history", [])
    
    if not scenario:
        return jsonify({"error": "No hay escenario para jugar"}), 400
    
    prompt = build_play_prompt(scenario, decision_index, choice_id, history)
    result = call_claude(prompt)
    
    return jsonify(result)


@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "api_configured": bool(ANTHROPIC_API_KEY),
        "model": ANTHROPIC_MODEL
    })


# ──────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
