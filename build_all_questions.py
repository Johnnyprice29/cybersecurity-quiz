#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script completo per:
1. Estrarre testo da TUTTI i PDF nelle cartelle 1-11
2. Generare file MD con domande, opzioni, risposte e giustificazioni
3. Rimuovere doppioni
4. Concatenare in un unico MD
5. Convertire in PDF
"""

import os
import re
import base64
import subprocess
import glob
from collections import OrderedDict

# Prova a importare PyMuPDF per l'estrazione PDF
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False
    print("[WARN] PyMuPDF non installato. Installare con: pip install pymupdf")

# Mapping delle cartelle ai moduli (ordinate da 1 a 11)
FOLDERS = OrderedDict([
    ("1 introduzione", ("01_Introduzione", "1. Introduzione")),
    ("2 sicurezza azienda", ("02_Sicurezza_Azienda", "2. Sicurezza in Azienda")),
    ("3 crittografia e documenti digitali", ("03_Crittografia_Documenti", "3. Crittografia e Documenti Digitali")),
    ("4 autenticazione", ("04_Autenticazione", "4. Autenticazione")),
    ("5 accessi remoti", ("05_Accessi_Remoti", "5. Accessi Remoti")),
    ("6 sicurezza reti", ("06_Sicurezza_Reti", "6. Sicurezza Reti")),
    ("7 protezione dati e canali", ("07_Protezione_Dati_Canali", "7. Protezione Dati e Canali")),
    ("8 firewall e perimetri", ("08_Firewall_Perimetri", "8. Firewall e Perimetri")),
    ("9 standard e normative", ("09_Standard_Normative", "9. Standard e Normative")),
    ("10 banche dati domande", ("10_Banca_Dati", "10. Banca Dati Domande")),
    ("11 simulazioni d'esame", ("11_Simulazioni_Esame", "11. Simulazioni d'Esame")),
])

OUTPUT_DIR = "DOMANDE"


def extract_text_from_pdf(pdf_path):
    """Estrae il testo da un file PDF usando PyMuPDF."""
    if not HAS_FITZ:
        return ""
    
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"[ERROR] Errore nell'estrazione di {pdf_path}: {e}")
        return ""


def clean_text(text):
    """Pulisce il testo delle domande rimuovendo elementi inutili."""
    if not text: return ""
    
    # Rimozione pattern comuni
    text = re.sub(r':\[html\]', '', text)
    text = re.sub(r'--- FILE:.*?---', '', text)
    text = re.sub(r'\d{1,2}/\d{1,2}/\d{2,4},?\s*\d{1,2}:\d{2}\s*[APM]{0,2}', '', text)
    text = re.sub(r'Punteggio ottenuto.*', '', text, flags=re.I)
    text = re.sub(r'Risposta (corretta|errata|parzialmente corretta|non data)', '', text, flags=re.I)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'Domanda \d+', '', text)
    text = re.sub(r'Rev(isione)? tentativo \| Moodle', '', text, flags=re.I)
    text = re.sub(r'Iniziato.*?Valutazione.*?\)', '', text, flags=re.DOTALL)
    text = re.sub(r'Stato Completato.*?%\)', '', text, flags=re.DOTALL)
    
    # Trova l'inizio della domanda vera e propria
    starts = [m.start() for m in re.finditer(
        r'\b(Quale|Quali|Cosa|In cosa|Che cosa|Descrivere|Come|A quali|Nell\'ambito|'
        r'Nel contesto|Dato un|E\' un|È un|Che |Perché|Vero o Falso|Definire|Qual è|'
        r'Chi |Definizione di|L\'|Un |Una |Se |Quando|Secondo|Considerando)', text)]
    if starts:
        text = text[starts[0]:]
    
    # Pulizia finale
    text = re.sub(r'^\d+/\d+', '', text).strip()
    text = re.sub(r'^[\s\.,:/|]+', '', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def get_justification(question_text, answer_text):
    """Genera una giustificazione basata sul contenuto della domanda."""
    combined = (question_text + " " + answer_text).lower()
    
    knowledge_base = {
        "stuxnet": "Stuxnet è un worm progettato per sabotare le centrifughe nucleari iraniane. Sfruttava 4 vulnerabilità zero-day e si diffondeva tramite USB in reti air-gapped. Il successo è dovuto a: sistemi privi di antivirus/firewall, servizi non necessari attivi, eccessiva fiducia nell'isolamento fisico.",
        "mirai": "Mirai è una botnet che infetta dispositivi IoT usando password di default non modificate. Viene utilizzata per attacchi DDoS volumetrici massivi.",
        "wannacry": "WannaCry è un ransomware che sfruttava EternalBlue (vulnerabilità SMB di Windows). Ha colpito globalmente nel 2017 cifrando i file e chiedendo riscatti in Bitcoin.",
        "phishing": "Il phishing è una tecnica di social engineering che usa messaggi ingannevoli per rubare credenziali. Lo Spear Phishing è mirato con dati personali, il Whaling colpisce dirigenti (CEO/CTO).",
        "whaling": "Il Whaling è una variante del phishing mirata specificamente a figure di alto livello come CEO, CTO o altri dirigenti aziendali.",
        "ransomware": "Ransomware cifra i dati e richiede un riscatto. Il modello RaaS (Ransomware as a Service) fornisce l'infrastruttura per diffonderlo in cambio di una commissione.",
        "man-in-the-middle|mitm": "L'attacco MITM intercetta la comunicazione tra due parti. Contromisure: garantire riservatezza, autenticazione, integrità e serializzazione di ogni pacchetto.",
        "ipsec": "IPsec opera a livello Network (L3). AH garantisce autenticità e integrità; ESP aggiunge la riservatezza cifrando il payload.",
        "tls|ssl": "TLS garantisce sessioni sicure a livello trasporto (L4). TLS 1.3 ha rimosso algoritmi obsoleti e ridotto la latenza dell'handshake.",
        "vpn": "Una VPN crea un tunnel sicuro su rete pubblica. IPsec è lo standard per site-to-site, SSL-VPN per accessi remoti.",
        "dmz": "La DMZ è un segmento di rete isolato per servizi pubblici (Web, Mail, DNS). Isola la rete interna da attacchi diretti da Internet.",
        "firewall": "Il firewall filtra il traffico in base a porte/IP (Packet Filter) o stato delle connessioni (Stateful Inspection). Può essere a livello applicativo (Proxy).",
        "ids|nids|hids": "NIDS monitora il traffico di rete; HIDS monitora file di log e integrità del sistema locale. Possono essere signature-based o anomaly-based.",
        "rsa": "RSA è un algoritmo asimmetrico basato sulla fattorizzazione di grandi numeri primi. Usato per scambio chiavi e firma digitale.",
        "aes": "AES (Advanced Encryption Standard) è un cifrario a blocchi simmetrico. Sostituto del DES, usa blocchi da 128 bit con chiavi da 128/192/256 bit.",
        "sha|hash": "Le funzioni hash producono un digest a lunghezza fissa. SHA-256 è lo standard minimo raccomandato. Garantiscono integrità dei dati.",
        "firma digitale": "La firma digitale garantisce autenticità, integrità e non-ripudio. Si cifra l'hash del messaggio con la propria chiave privata.",
        "iso 27001": "ISO 27001 è lo standard internazionale per i Sistemi di Gestione della Sicurezza delle Informazioni (ISMS). Approccio orientato al rischio.",
        "gdpr": "GDPR è il regolamento UE sulla protezione dei dati. Introduce Privacy by Design/Default e obbligo di notifica data breach entro 72 ore.",
        "common criteria": "Common Criteria (ISO 15408) è lo standard internazionale per certificare la sicurezza dei prodotti IT tramite livelli EAL.",
        "kerberos": "Kerberos è un protocollo di autenticazione a ticket basato su KDC (Key Distribution Center). Previene lo sniffing delle password.",
        "radius": "RADIUS è un protocollo AAA per autenticazione centralizzata. Cifra solo la password (TACACS+ cifra tutto).",
        "xss": "XSS (Cross-Site Scripting) inietta script nel browser della vittima. Si previene con validazione e sanitizzazione degli input.",
        "sql injection": "SQL Injection manipola il database tramite input malevoli. Si previene con query parametrizzate (prepared statements).",
        "diffie-hellman|dh": "Diffie-Hellman permette lo scambio sicuro di chiavi su canale pubblico. La sicurezza si basa sul problema del logaritmo discreto.",
        "dnssec": "DNSSEC protegge il DNS dal cache poisoning tramite firme digitali. Non cifra le query, solo ne garantisce l'autenticità.",
        "dos|ddos": "DoS/DDoS tiene impegnato un host impedendogli di fornire servizi. DDoS usa una botnet per amplificare l'attacco.",
        "syn flood|syn cookie": "SYN Flooding esaurisce le risorse del server con richieste incomplete. I SYN Cookie evitano di allocare risorse prima del completamento dell'handshake.",
        "worm": "Un worm è un malware che si replica autonomamente saturando le risorse, senza necessità di intervento umano (a differenza dei virus).",
        "virus": "Un virus si replica e causa danni, ma richiede l'intervento umano (involontario) per propagarsi.",
        "trojan": "Un Trojan si maschera da software legittimo ma esegue azioni malevole. Non si replica autonomamente.",
        "rootkit": "Un Rootkit è un insieme di tool che consentono di ottenere permessi di root e nascondere la propria presenza nel sistema.",
        "backdoor": "Una backdoor è un accesso nascosto al sistema, spesso usato per aggiornamenti remoti ma sfruttabile da attaccanti.",
        "social engineering": "Il Social Engineering sfrutta debolezze umane (fiducia, urgenza) per ottenere informazioni o accessi non autorizzati.",
        "pretexting": "Pretexting crea uno scenario falso per indurre la vittima a cooperare e rivelare informazioni sensibili.",
        "spoofing|ip spoofing": "IP Spoofing falsifica l'indirizzo IP sorgente per impersonare qualcun altro. Contromisura: non usare mai gli IP per autenticazione.",
        "sniffing|packet sniffing": "Packet Sniffing intercetta passivamente i pacchetti di rete. Contromisura: cifratura del traffico (TLS, SSH, VPN).",
        "shadow server": "Uno Shadow Server si pone come fornitore di un servizio senza averne il diritto. Contromisura: autenticazione del server.",
        "security by design": "Security by Design integra le misure di sicurezza fin dall'inizio della progettazione del sistema.",
        "security by default": "Security by Default implementa le migliori protezioni di sicurezza attive di default, senza interventi manuali.",
        "defense in depth": "Defense in Depth crea strati multipli di difesa per proteggere il sistema da diverse minacce.",
        "need to know": "Need to Know fornisce all'utente solo le informazioni strettamente necessarie per svolgere il proprio lavoro.",
        "least privilege": "Least Privilege fornisce all'utente solo le autorizzazioni minime necessarie per svolgere il proprio lavoro.",
        "non ripudio": "Il non-ripudio è una prova innegabile, riconosciuta dalla legge, per dimostrare chi è l'autore di dati o azioni.",
        "autenticazione": "L'autenticazione verifica la veridicità di un'asserzione enunciata da qualche entità.",
        "integrità": "L'integrità garantisce che i dati non siano stati modificati, cancellati o duplicati.",
        "riservatezza|confidenzialità": "La riservatezza garantisce che le informazioni siano accessibili solo a chi è autorizzato.",
        "disponibilità": "La disponibilità garantisce che i servizi siano accessibili quando necessario.",
        "data at rest": "Data at rest: dati memorizzati su un dispositivo (disco, database).",
        "data in transit": "Data in transit: dati trasmessi su un canale di comunicazione.",
        "apt|advanced persistent threat": "APT (Advanced Persistent Threat) sono attacchi sofisticati e prolungati, spesso sponsorizzati da stati.",
        "blue born": "Blue Born è un worm che si diffonde attraverso vulnerabilità nel Bluetooth, colpendo anche autoveicoli.",
        "black energy": "Black Energy è un malware progettato per rimanere nascosto il più a lungo possibile (APT), usato in attacchi alle infrastrutture critiche.",
        "crime-as-a-service|caas": "CaaS (Crime-as-a-Service) offre servizi criminali sul dark web: vendita di vulnerabilità, dati, server compromessi.",
        "malware as a service": "Malware as a Service fornisce accesso a software malevolo e infrastruttura correlata a pagamento, con vari piani di cooperazione.",
        "sybil": "L'attacco Sybil crea molteplici identità fittizie per sovvertire sistemi di reputazione o votazione.",
        "bastion host": "Un Bastion Host è un server esposto all'esterno, appositamente hardened per resistere agli attacchi.",
        "dual-homed": "Architettura firewall con due schede di rete che isola fisicamente rete interna ed esterna.",
        "proxy": "Un Proxy agisce da intermediario, nascondendo l'IP del client e permettendo filtraggio applicativo.",
        "nat": "Il NAT nasconde gli indirizzi IP interni traducendoli in un unico IP pubblico.",
        "pki|certificat": "PKI gestisce certificati digitali per l'autenticazione e la cifratura tramite Certification Authority (CA).",
        "ocsp|crl": "OCSP verifica in tempo reale lo stato di revoca di un certificato, più efficiente delle CRL.",
        "smime|s/mime": "S/MIME aggiunge firma e cifratura alle email a livello applicativo (end-to-end).",
        "dkim": "DKIM associa un'identità di dominio a un messaggio email tramite firma digitale verificabile via DNS.",
        "spf": "SPF specifica quali server sono autorizzati a inviare email per un dominio.",
        "dmarc": "DMARC combina SPF e DKIM per proteggere i domini email da spoofing.",
        "wpa|wpa2|wpa3": "WPA3 migliora WPA2 con SAE (Simultaneous Authentication of Equals) contro attacchi offline alle password.",
        "mfa|multi-factor": "MFA combina più fattori: qualcosa che sai (password), che hai (token), che sei (biometria).",
        "otp": "OTP (One-Time Password) sono password monouso, generate da token hardware o app.",
        "rbac": "RBAC (Role-Based Access Control) assegna permessi in base ai ruoli aziendali, non alle singole identità.",
        "pfs|perfect forward secrecy": "PFS garantisce che la compromissione di una chiave non comprometta le sessioni passate.",
        "nonce": "Un nonce è un numero usato una sola volta per prevenire attacchi di replay.",
        "cifrario|cifratura simmetrica": "La cifratura simmetrica usa la stessa chiave per cifrare e decifrare. Veloce ma richiede scambio sicuro della chiave.",
        "cifratura asimmetrica": "La cifratura asimmetrica usa coppia di chiavi pubblica/privata. Più lenta ma risolve il problema dello scambio chiavi.",
        "mac|message authentication code": "Il MAC garantisce integrità e autenticità usando una chiave segreta condivisa.",
        "hmac": "HMAC è un MAC basato su funzione hash, più sicuro del MAC tradizionale.",
        "cbc|ecb|gcm": "ECB è insicuro (pattern visibili), CBC usa IV e concatena blocchi, GCM fornisce anche autenticazione (AEAD).",
        "challenge-response": "Challenge-Response: il server invia una sfida casuale, il client risponde con il valore corretto dimostrando la conoscenza del segreto.",
        "owasp": "OWASP Top 10 elenca le vulnerabilità web più critiche: injection, broken auth, XSS, insecure deserialization, etc.",
        "penetration test": "Il Penetration Test simula attacchi autorizzati per verificare le difese del sistema.",
        "vulnerability assessment": "Vulnerability Assessment identifica e classifica le vulnerabilità senza sfruttarle attivamente.",
        "siem": "SIEM aggrega log e correla eventi da diverse fonti per identificare attacchi complessi.",
        "soc": "SOC (Security Operations Center) monitora h24 la sicurezza e coordina le risposte agli incidenti.",
    }
    
    for key, justification in knowledge_base.items():
        if any(k in combined for k in key.split('|')):
            return justification
    
    return "Analisi delle proprietà di sicurezza (CIA: Confidentiality, Integrity, Availability) e delle contromisure appropriate."


def extract_questions_from_text(content):
    """Estrae tutte le domande da un testo."""
    questions = []
    
    # Split basato sul pattern "La risposta corretta è:" o "Le risposte corrette sono:"
    chunks = re.split(r'(?:La risposta corretta è:|Le risposte corrette sono:)', content)
    
    for i in range(len(chunks) - 1):
        segment = chunks[i]
        answer_part = chunks[i + 1]
        
        # Estrai la risposta (prime righe dopo il split)
        answer_lines = []
        for line in answer_part.split('\n'):
            line = line.strip()
            if not line:
                continue
            # La risposta termina quando troviamo un nuovo pattern
            if re.match(r'^(Domanda \d+|Iniziato|Stato Completato|\d{1,2}/\d{1,2}/\d{2})', line):
                break
            answer_lines.append(line)
            if len(answer_lines) >= 5:
                break
        
        answer = ' '.join(answer_lines).strip()
        # Rimuovi rumore dalla risposta
        answer = re.sub(r'\d{1,2}/\d{1,2}/\d{2,4}.*$', '', answer).strip()
        
        # Estrai domanda e opzioni dal segmento
        lines = [l.strip() for l in segment.split('\n') if l.strip()]
        
        # Trova le opzioni
        options = []
        question_end_idx = 0
        
        for idx, line in enumerate(lines):
            if re.match(r'^[a-z]\.\s', line):
                options.append(line)
                if question_end_idx == 0:
                    question_end_idx = idx
            elif line in ["Vero", "Falso"]:
                options.append(line)
                if question_end_idx == 0:
                    question_end_idx = idx
        
        # La domanda sono le righe prima delle opzioni
        if question_end_idx > 0:
            question_lines = lines[:question_end_idx]
        else:
            question_lines = lines[-10:] if len(lines) > 10 else lines
        
        question_text = clean_text(' '.join(question_lines))
        
        # Ignora domande troppo corte o invalide
        if len(question_text) < 20:
            continue
        
        questions.append({
            'text': question_text,
            'options': options,
            'answer': answer
        })
    
    return questions


def deduplicate_questions(all_questions):
    """Rimuove domande duplicate basandosi sul testo normalizzato."""
    seen = {}
    unique = []
    
    for q in all_questions:
        # Normalizza per confronto
        key = re.sub(r'[^\w\s]', '', q['text'].lower())
        key = re.sub(r'\s+', ' ', key).strip()[:100]  # Primi 100 caratteri
        
        if key not in seen:
            seen[key] = q
            unique.append(q)
        else:
            # Se troviamo una versione con più opzioni, aggiorniamo
            if len(q['options']) > len(seen[key]['options']):
                idx = unique.index(seen[key])
                unique[idx] = q
                seen[key] = q
    
    return unique


def generate_module_markdown(module_name, module_title, questions):
    """Genera il contenuto markdown per un modulo."""
    lines = []
    lines.append(f"# {module_title}")
    lines.append("")
    lines.append(f"*Totale domande: {len(questions)}*")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    for idx, q in enumerate(questions, 1):
        lines.append(f"## Domanda {idx}")
        lines.append("")
        lines.append(f"**{q['text']}**")
        lines.append("")
        
        if q['options']:
            lines.append("**Opzioni:**")
            for opt in q['options']:
                lines.append(f"- {opt}")
            lines.append("")
        
        lines.append(f"**✓ Risposta corretta:** {q['answer']}")
        lines.append("")
        
        justification = get_justification(q['text'], q['answer'])
        lines.append(f"*Giustificazione:* {justification}")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    return '\n'.join(lines)


def md_to_pdf(md_path):
    """Converte un file markdown in PDF usando Chrome headless."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
        os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe"),
    ]
    
    browser = None
    for p in candidates:
        if os.path.isfile(p):
            browser = p
            break
    
    if not browser:
        print(f"[WARN] Browser non trovato, impossibile convertire {md_path}")
        return False
    
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    html_template = """<!DOCTYPE html>
<html lang='it'>
<head>
<meta charset='UTF-8'>
<title>{title}</title>
<link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown.min.css'>
<style>
.markdown-body {{
  box-sizing: border-box;
  min-width: 200px;
  max-width: 980px;
  margin: 0 auto;
  padding: 45px;
  font-size: 14px;
}}
@media print {{ 
  .markdown-body {{ max-width: none; padding: 20px; }} 
  body {{ background-color: white; }}
}}
</style>
<script src='https://cdn.jsdelivr.net/npm/markdown-it@13.0.1/dist/markdown-it.min.js'></script>
</head>
<body>
<article class='markdown-body' id='content'>Loading…</article>
<div id='raw-content' style='display:none;'>{b64_content}</div>
<script>
function decodeContent(str) {{
  return decodeURIComponent(atob(str).split('').map(function(c) {{
    return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
  }}).join(''));
}}
document.addEventListener('DOMContentLoaded', function() {{
  const md = window.markdownit({{ html:true, breaks:true, linkify:true }});
  const raw = document.getElementById('raw-content').textContent;
  const markdown = decodeContent(raw);
  document.getElementById('content').innerHTML = md.render(markdown);
}});
</script>
</body>
</html>"""
    
    b64 = base64.b64encode(md_content.encode('utf-8')).decode('utf-8')
    title = os.path.splitext(os.path.basename(md_path))[0]
    html = html_template.format(title=title, b64_content=b64)
    
    temp_html = md_path.replace('.md', '.temp.html')
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(html)
    
    pdf_path = md_path.replace('.md', '.pdf')
    abs_html = os.path.abspath(temp_html)
    abs_pdf = os.path.abspath(pdf_path)
    file_uri = f"file:///{abs_html.replace(os.sep, '/')}"
    
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        f"--print-to-pdf={abs_pdf}",
        "--no-pdf-header-footer",
        file_uri,
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        success = os.path.isfile(abs_pdf)
    except Exception as e:
        print(f"[ERROR] Conversione fallita per {md_path}: {e}")
        success = False
    
    try:
        os.remove(temp_html)
    except:
        pass
    
    return success


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)
    
    if not HAS_FITZ:
        print("=" * 60)
        print("ERRORE: PyMuPDF non è installato!")
        print("Esegui: pip install pymupdf")
        print("=" * 60)
        return
    
    all_modules_content = []
    total_questions = 0
    
    print("=" * 60)
    print("GENERAZIONE BANCA DATI DOMANDE")
    print("Estrazione da TUTTI i PDF nelle cartelle 1-11")
    print("=" * 60)
    print()
    
    for folder_name, (module_code, module_title) in FOLDERS.items():
        folder_path = os.path.join(base_dir, folder_name)
        
        if not os.path.isdir(folder_path):
            print(f"[SKIP] Cartella non trovata: {folder_name}")
            continue
        
        print(f"[PROCESSING] {module_title}...")
        
        # Trova tutti i PDF nella cartella
        pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))
        
        if not pdf_files:
            print(f"  → Nessun PDF trovato")
            continue
        
        print(f"  → {len(pdf_files)} PDF trovati")
        
        # Estrai testo da tutti i PDF
        all_text = ""
        for pdf_file in pdf_files:
            print(f"     Estrazione: {os.path.basename(pdf_file)}")
            text = extract_text_from_pdf(pdf_file)
            all_text += f"\n\n--- FILE: {os.path.basename(pdf_file)} ---\n\n{text}"
        
        # Estrai domande dal testo combinato
        questions = extract_questions_from_text(all_text)
        questions = deduplicate_questions(questions)
        
        if not questions:
            print(f"  → Nessuna domanda trovata")
            continue
        
        print(f"  → {len(questions)} domande uniche estratte")
        total_questions += len(questions)
        
        # Genera markdown per il modulo
        md_content = generate_module_markdown(module_code, module_title, questions)
        
        # Salva file MD del modulo
        md_path = os.path.join(output_dir, f"{module_code}.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"  → Salvato: {module_code}.md")
        
        # Aggiungi al contenuto concatenato
        all_modules_content.append(md_content)
    
    print()
    print("=" * 60)
    print(f"TOTALE DOMANDE ESTRATTE: {total_questions}")
    print("=" * 60)
    print()
    
    # Genera file concatenato
    print("[GENERATING] File concatenato...")
    concat_content = "\n\n---\n\n".join(all_modules_content)
    
    header = """# Banca Dati Completa - Sicurezza Informatica

## Indice dei Moduli

1. Introduzione
2. Sicurezza in Azienda
3. Crittografia e Documenti Digitali
4. Autenticazione
5. Accessi Remoti
6. Sicurezza Reti
7. Protezione Dati e Canali
8. Firewall e Perimetri
9. Standard e Normative
10. Banca Dati Domande
11. Simulazioni d'Esame

---

"""
    
    concat_path = os.path.join(output_dir, "Domande_Totali.md")
    with open(concat_path, 'w', encoding='utf-8') as f:
        f.write(header + concat_content)
    print(f"  → Salvato: Domande_Totali.md")
    
    # Converti tutti i file MD in PDF
    print()
    print("[CONVERTING] Conversione in PDF...")
    
    md_files = sorted(glob.glob(os.path.join(output_dir, "*.md")))
    for md_file in md_files:
        basename = os.path.basename(md_file)
        print(f"  → Convertendo: {basename}")
        if md_to_pdf(md_file):
            print(f"     ✓ PDF creato")
        else:
            print(f"     ✗ Conversione fallita")
    
    print()
    print("=" * 60)
    print("COMPLETATO!")
    print(f"Output in: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
