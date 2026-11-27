import os,json
from openai import OpenAI

ROLES = {
"market_scout":"Find zero-upfront-cost customer problems and underserved demand. Prefer reachable customers and urgent problems.",
"offer_designer":"Turn plausible customer problems into a specific service or digital deliverable that can be sold before spending money.",
"growth_analyst":"Find practical, non-spam ways to reach first customers and repeat buyers without paid ads.",
"skeptical_reviewer":"Attack weak assumptions, identify competition and failure risks, and suggest the cheapest validation test."
}
RULES = """You are one specialist inside ZERO TO PROFIT. Starting capital is exactly €0.
Focus on legitimate value exchange: services, freelancing, digital products, content,
research, automation and customer-funded work. Avoid scams, deception, spam, fake
engagement, unlawful activity and platform-rule evasion. Never claim money was earned
unless a verified ledger entry exists. No paid tools or ad spend in a zero-capital plan.
Return concise, concrete and testable advice. Distinguish evidence from assumptions."""
def ask(role, prompt):
    key=os.getenv("OPENAI_API_KEY","").strip()
    if not key: return {"report":f"Demo mode: configure OPENAI_API_KEY to activate {role}.", "ideas":[]}
    client=OpenAI(api_key=key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
    r=client.chat.completions.create(model=os.getenv("OPENAI_MODEL","gpt-6"),
       messages=[{"role":"system","content":RULES+"\nRole: "+ROLES[role]+"\nReturn JSON only."},
                 {"role":"user","content":prompt}],
       response_format={"type":"json_object"})
    return json.loads(r.choices[0].message.content)
def orchestrate(state):
    history=json.dumps(state.get("events",[])[:12],ensure_ascii=False)
    prompt="Recent memory:\n"+history+"\nCreate a new research report and up to 5 opportunities. JSON schema: {report:string, ideas:[{title,customer,problem,offer,first_step,score integer 1-10}]}"
    reports=[]
    for role in ROLES:
        try: reports.append((role,ask(role,prompt)))
        except Exception as e: reports.append((role,{"report":f"Role failed: {e}","ideas":[]}))
    combined={"reports":reports}
    # Synthesise from role outputs into a focused next step
    if os.getenv("OPENAI_API_KEY","").strip():
        try:
            synth=ask("skeptical_reviewer","Synthesize these specialist reports into JSON with keys summary, next_experiment, hypothesis, success_metric, and code_improvement (title,rationale,patch). Reports:\n"+json.dumps(reports,ensure_ascii=False)[:12000])
            combined["synthesis"]=synth
        except Exception as e: combined["synthesis"]={"summary":str(e),"next_experiment":"Review the reports manually."}
    else:
        combined["synthesis"]={"summary":"Demo cycle completed. Add an API key for live multi-agent reasoning.","next_experiment":"Pick one zero-cost service, create a sample, and validate demand with a small number of relevant prospects.","hypothesis":"A clearly scoped service solves a real problem for an identifiable buyer.","success_metric":"One qualified reply or one paid pilot within 7 days."}
    return combined
