#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script per estrarre il testo da TUTTI i PDF nelle cartelle 1-11.
Salva il testo estratto in file .txt nella cartella DOMANDE.
"""

import os
import glob

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Errore: PyMuPDF non installato. Esegui: pip install pymupdf")
    exit(1)

# Cartelle da processare (1-11)
FOLDERS = [
    "1 introduzione",
    "2 sicurezza azienda",
    "3 crittografia e documenti digitali",
    "4 autenticazione",
    "5 accessi remoti",
    "6 sicurezza reti",
    "7 protezione dati e canali",
    "8 firewall e perimetri",
    "9 standard e normative",
    "10 banche dati domande",
    "11 simulazioni d'esame",
]

OUTPUT_DIR = "DOMANDE"


def extract_text_from_pdf(pdf_path):
    """Estrae il testo da un PDF."""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"  [ERRORE] {e}")
        return ""


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 60)
    print("ESTRAZIONE TESTO DA PDF")
    print("=" * 60)
    print()
    
    for folder in FOLDERS:
        folder_path = os.path.join(base_dir, folder)
        
        if not os.path.isdir(folder_path):
            print(f"[SKIP] Cartella non trovata: {folder}")
            continue
        
        # Trova tutti i PDF
        pdf_files = sorted(glob.glob(os.path.join(folder_path, "*.pdf")))
        
        if not pdf_files:
            print(f"[SKIP] Nessun PDF in: {folder}")
            continue
        
        print(f"[{folder}] - {len(pdf_files)} PDF")
        
        # Estrai testo da ogni PDF
        all_text = ""
        for pdf_file in pdf_files:
            pdf_name = os.path.basename(pdf_file)
            print(f"  → {pdf_name}")
            text = extract_text_from_pdf(pdf_file)
            all_text += f"\n\n{'='*60}\n=== {pdf_name} ===\n{'='*60}\n\n{text}"
        
        # Salva il testo estratto
        # Creo nome file dal numero cartella
        folder_num = folder.split()[0].zfill(2)
        output_file = os.path.join(output_dir, f"{folder_num}_extracted.txt")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(all_text)
        
        print(f"  ✓ Salvato: {folder_num}_extracted.txt")
        print()
    
    print("=" * 60)
    print(f"COMPLETATO! File in: {OUTPUT_DIR}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
