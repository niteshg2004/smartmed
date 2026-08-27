"""
python manage.py seed_demo_data

Comprehensive demo data generator for SmartMed PBL project.
Creates realistic demo data for development, testing, and ML experimentation:
  - 4 demo user accounts (admin, 2 pharmacy owners, 1 patient)
  - 100+ medicines covering common Indian pharmacy brands
  - 10 pharmacies with realistic coordinates (Pune, India)
  - Inventory records linking pharmacies to medicines
  - 30-90 days of inventory history (for ML training)
  - Alternative medicine candidates

All generated records are marked with is_demo_data=True.
Running the command again is safe — it skips already-seeded data.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User


DEMO_PASSWORD = "SmartMed@Demo123"

DEMO_USERS = [
    {"email": "admin@smartmed.demo", "name": "SmartMed Admin", "role": User.Role.ADMIN, "is_staff": True, "is_superuser": True},
    {"email": "pharmacy1@smartmed.demo", "name": "Apollo Pharmacy Owner", "role": User.Role.PHARMACY},
    {"email": "pharmacy2@smartmed.demo", "name": "MedPlus Pharmacy Owner", "role": User.Role.PHARMACY},
    {"email": "patient1@smartmed.demo", "name": "Demo Patient", "role": User.Role.PATIENT},
]

# ---------------------------------------------------------------------------
# 100+ realistic Indian pharmacy medicines
# ---------------------------------------------------------------------------
MEDICINES = [
    # Analgesics / Antipyretics
    {"brand_name": "Dolo 650", "generic_name": "Paracetamol", "composition": "Paracetamol", "strength": "650mg", "dosage_form": "tablet", "manufacturer": "Micro Labs", "therapeutic_category": "Analgesic / Antipyretic", "prescription_required": False, "description": "Used for fever and mild to moderate pain relief."},
    {"brand_name": "Crocin Advance", "generic_name": "Paracetamol", "composition": "Paracetamol", "strength": "500mg", "dosage_form": "tablet", "manufacturer": "GSK", "therapeutic_category": "Analgesic / Antipyretic", "prescription_required": False, "description": "Pain and fever relief."},
    {"brand_name": "Calpol", "generic_name": "Paracetamol", "composition": "Paracetamol", "strength": "500mg/5ml", "dosage_form": "syrup", "manufacturer": "GSK", "therapeutic_category": "Analgesic / Antipyretic", "prescription_required": False, "description": "Paediatric fever and pain syrup."},
    {"brand_name": "Combiflam", "generic_name": "Ibuprofen + Paracetamol", "composition": "Ibuprofen + Paracetamol", "strength": "400mg+325mg", "dosage_form": "tablet", "manufacturer": "Sanofi", "therapeutic_category": "Analgesic / Antipyretic", "prescription_required": False, "description": "Combination pain and inflammation relief."},
    {"brand_name": "Sumo", "generic_name": "Nimesulide + Paracetamol", "composition": "Nimesulide + Paracetamol", "strength": "100mg+325mg", "dosage_form": "tablet", "manufacturer": "Alkem", "therapeutic_category": "Analgesic / Antipyretic", "prescription_required": True, "description": "Pain and inflammation relief."},
    {"brand_name": "Zerodol SP", "generic_name": "Aceclofenac + Paracetamol + Serratiopeptidase", "composition": "Aceclofenac + Paracetamol + Serratiopeptidase", "strength": "100mg+325mg+15mg", "dosage_form": "tablet", "manufacturer": "IPCA Labs", "therapeutic_category": "Analgesic / Anti-inflammatory", "prescription_required": True, "description": "Anti-inflammatory with muscle relaxant."},
    {"brand_name": "Voveran SR", "generic_name": "Diclofenac Sodium", "composition": "Diclofenac Sodium", "strength": "100mg", "dosage_form": "tablet", "manufacturer": "Novartis", "therapeutic_category": "Analgesic / Anti-inflammatory", "prescription_required": True, "description": "NSAID for pain and inflammation."},
    {"brand_name": "Disprin", "generic_name": "Aspirin", "composition": "Aspirin", "strength": "350mg", "dosage_form": "tablet", "manufacturer": "Reckitt", "therapeutic_category": "Analgesic / Antipyretic", "prescription_required": False, "description": "Pain relief and blood thinner."},
    {"brand_name": "Saridon", "generic_name": "Propyphenazone + Paracetamol + Caffeine", "composition": "Propyphenazone + Paracetamol + Caffeine", "strength": "150mg+250mg+50mg", "dosage_form": "tablet", "manufacturer": "Bayer", "therapeutic_category": "Analgesic / Antipyretic", "prescription_required": False, "description": "Headache and body pain relief."},
    {"brand_name": "Meftal Spas", "generic_name": "Mefenamic Acid + Dicyclomine", "composition": "Mefenamic Acid + Dicyclomine", "strength": "250mg+10mg", "dosage_form": "tablet", "manufacturer": "Blue Cross", "therapeutic_category": "Antispasmodic / Analgesic", "prescription_required": True, "description": "For menstrual and abdominal cramps."},

    # Antibiotics
    {"brand_name": "Augmentin 625 Duo", "generic_name": "Amoxicillin + Clavulanic Acid", "composition": "Amoxicillin + Clavulanic Acid", "strength": "500mg+125mg", "dosage_form": "tablet", "manufacturer": "GSK", "therapeutic_category": "Antibiotic", "prescription_required": True, "description": "Broad-spectrum antibiotic for bacterial infections."},
    {"brand_name": "Azithral 500", "generic_name": "Azithromycin", "composition": "Azithromycin", "strength": "500mg", "dosage_form": "tablet", "manufacturer": "Alembic", "therapeutic_category": "Antibiotic", "prescription_required": True, "description": "Macrolide antibiotic for respiratory and skin infections."},
    {"brand_name": "Cifran 500", "generic_name": "Ciprofloxacin", "composition": "Ciprofloxacin", "strength": "500mg", "dosage_form": "tablet", "manufacturer": "Sun Pharma", "therapeutic_category": "Antibiotic", "prescription_required": True, "description": "Fluoroquinolone antibiotic for UTI and other infections."},
    {"brand_name": "Monocef 200", "generic_name": "Cefixime", "composition": "Cefixime", "strength": "200mg", "dosage_form": "tablet", "manufacturer": "Aristo", "therapeutic_category": "Antibiotic", "prescription_required": True, "description": "Cephalosporin antibiotic."},
    {"brand_name": "Amoxyclav 625", "generic_name": "Amoxicillin + Clavulanic Acid", "composition": "Amoxicillin + Clavulanic Acid", "strength": "500mg+125mg", "dosage_form": "tablet", "manufacturer": "Cipla", "therapeutic_category": "Antibiotic", "prescription_required": True, "description": "Broad-spectrum antibiotic."},
    {"brand_name": "Moxikind CV 625", "generic_name": "Amoxicillin + Clavulanic Acid", "composition": "Amoxicillin + Clavulanic Acid", "strength": "500mg+125mg", "dosage_form": "tablet", "manufacturer": "Mankind", "therapeutic_category": "Antibiotic", "prescription_required": True, "description": "Antibiotic for bacterial infections."},
    {"brand_name": "Ciplox 500", "generic_name": "Ciprofloxacin", "composition": "Ciprofloxacin", "strength": "500mg", "dosage_form": "tablet", "manufacturer": "Cipla", "therapeutic_category": "Antibiotic", "prescription_required": True, "description": "Fluoroquinolone antibiotic."},
    {"brand_name": "Doxycycline 100", "generic_name": "Doxycycline", "composition": "Doxycycline", "strength": "100mg", "dosage_form": "capsule", "manufacturer": "Sun Pharma", "therapeutic_category": "Antibiotic", "prescription_required": True, "description": "Tetracycline antibiotic."},
    {"brand_name": "Metrogyl 400", "generic_name": "Metronidazole", "composition": "Metronidazole", "strength": "400mg", "dosage_form": "tablet", "manufacturer": "J&J", "therapeutic_category": "Antibiotic / Antiprotozoal", "prescription_required": True, "description": "For anaerobic and protozoal infections."},
    {"brand_name": "Norflox TZ", "generic_name": "Norfloxacin + Tinidazole", "composition": "Norfloxacin + Tinidazole", "strength": "400mg+600mg", "dosage_form": "tablet", "manufacturer": "Cipla", "therapeutic_category": "Antibiotic", "prescription_required": True, "description": "For GI and urinary infections."},

    # Antacids / GI
    {"brand_name": "Pan 40", "generic_name": "Pantoprazole", "composition": "Pantoprazole", "strength": "40mg", "dosage_form": "tablet", "manufacturer": "Alkem", "therapeutic_category": "Antacid / PPI", "prescription_required": True, "description": "Proton pump inhibitor for acid reflux and GERD."},
    {"brand_name": "Omez 20", "generic_name": "Omeprazole", "composition": "Omeprazole", "strength": "20mg", "dosage_form": "capsule", "manufacturer": "Dr. Reddy's", "therapeutic_category": "Antacid / PPI", "prescription_required": True, "description": "Proton pump inhibitor."},
    {"brand_name": "Rantac 150", "generic_name": "Ranitidine", "composition": "Ranitidine", "strength": "150mg", "dosage_form": "tablet", "manufacturer": "J&J", "therapeutic_category": "Antacid / H2 Blocker", "prescription_required": False, "description": "H2 blocker for acid reflux."},
    {"brand_name": "Gelusil MPS", "generic_name": "Aluminium + Magnesium + Simethicone", "composition": "Aluminium Hydroxide + Magnesium Hydroxide + Simethicone", "strength": "250mg+250mg+50mg", "dosage_form": "tablet", "manufacturer": "Pfizer", "therapeutic_category": "Antacid", "prescription_required": False, "description": "Chewable antacid for acidity and gas."},
    {"brand_name": "Digene", "generic_name": "Aluminium + Magnesium", "composition": "Dried Aluminium Hydroxide + Magnesium Aluminium Silicate Hydrate", "strength": "830mg", "dosage_form": "tablet", "manufacturer": "Abbott", "therapeutic_category": "Antacid", "prescription_required": False, "description": "Antacid for acidity and indigestion."},
    {"brand_name": "Pantocid 40", "generic_name": "Pantoprazole", "composition": "Pantoprazole", "strength": "40mg", "dosage_form": "tablet", "manufacturer": "Sun Pharma", "therapeutic_category": "Antacid / PPI", "prescription_required": True, "description": "PPI for acid reflux and GERD."},
    {"brand_name": "Rablet 20", "generic_name": "Rabeprazole", "composition": "Rabeprazole", "strength": "20mg", "dosage_form": "tablet", "manufacturer": "Lupin", "therapeutic_category": "Antacid / PPI", "prescription_required": True, "description": "PPI for acid-related disorders."},
    {"brand_name": "Mucaine Gel", "generic_name": "Aluminium + Magnesium + Oxetacaine", "composition": "Aluminium Hydroxide + Magnesium Hydroxide + Oxetacaine", "strength": "291mg+98mg+10mg", "dosage_form": "syrup", "manufacturer": "Pfizer", "therapeutic_category": "Antacid", "prescription_required": False, "description": "Antacid gel with local anaesthetic."},
    {"brand_name": "Domperidone 10", "generic_name": "Domperidone", "composition": "Domperidone", "strength": "10mg", "dosage_form": "tablet", "manufacturer": "Sun Pharma", "therapeutic_category": "Antiemetic / Prokinetic", "prescription_required": True, "description": "For nausea and vomiting."},
    {"brand_name": "Ondansetron 4", "generic_name": "Ondansetron", "composition": "Ondansetron", "strength": "4mg", "dosage_form": "tablet", "manufacturer": "Cipla", "therapeutic_category": "Antiemetic", "prescription_required": True, "description": "For nausea and vomiting."},

    # Antihistamines / Allergy
    {"brand_name": "Cetirizine 10", "generic_name": "Cetirizine", "composition": "Cetirizine", "strength": "10mg", "dosage_form": "tablet", "manufacturer": "Cipla", "therapeutic_category": "Antihistamine", "prescription_required": False, "description": "For allergic rhinitis and urticaria."},
    {"brand_name": "Allegra 120", "generic_name": "Fexofenadine", "composition": "Fexofenadine", "strength": "120mg", "dosage_form": "tablet", "manufacturer": "Sanofi", "therapeutic_category": "Antihistamine", "prescription_required": False, "description": "Non-drowsy antihistamine."},
    {"brand_name": "Montair LC", "generic_name": "Montelukast + Levocetirizine", "composition": "Montelukast + Levocetirizine", "strength": "10mg+5mg", "dosage_form": "tablet", "manufacturer": "Cipla", "therapeutic_category": "Antihistamine / Antileukotriene", "prescription_required": True, "description": "For allergic rhinitis and asthma."},
    {"brand_name": "Levocet 5", "generic_name": "Levocetirizine", "composition": "Levocetirizine", "strength": "5mg", "dosage_form": "tablet", "manufacturer": "Sun Pharma", "therapeutic_category": "Antihistamine", "prescription_required": False, "description": "For allergies and hives."},
    {"brand_name": "Avil 25", "generic_name": "Pheniramine", "composition": "Pheniramine Maleate", "strength": "25mg", "dosage_form": "tablet", "manufacturer": "Sanofi", "therapeutic_category": "Antihistamine", "prescription_required": False, "description": "First-generation antihistamine."},

    # Antidiabetic
    {"brand_name": "Glycomet 500", "generic_name": "Metformin", "composition": "Metformin", "strength": "500mg", "dosage_form": "tablet", "manufacturer": "USV", "therapeutic_category": "Antidiabetic", "prescription_required": True, "description": "Oral hypoglycaemic for type 2 diabetes."},
    {"brand_name": "Glycomet GP 1", "generic_name": "Metformin + Glimepiride", "composition": "Metformin + Glimepiride", "strength": "500mg+1mg", "dosage_form": "tablet", "manufacturer": "USV", "therapeutic_category": "Antidiabetic", "prescription_required": True, "description": "Combination antidiabetic."},
    {"brand_name": "Janumet 50/500", "generic_name": "Sitagliptin + Metformin", "composition": "Sitagliptin + Metformin", "strength": "50mg+500mg", "dosage_form": "tablet", "manufacturer": "MSD", "therapeutic_category": "Antidiabetic", "prescription_required": True, "description": "DPP-4 inhibitor + Metformin combination."},
    {"brand_name": "Galvus Met 50/500", "generic_name": "Vildagliptin + Metformin", "composition": "Vildagliptin + Metformin", "strength": "50mg+500mg", "dosage_form": "tablet", "manufacturer": "Novartis", "therapeutic_category": "Antidiabetic", "prescription_required": True, "description": "DPP-4 inhibitor + Metformin combination."},
    {"brand_name": "Amaryl 2", "generic_name": "Glimepiride", "composition": "Glimepiride", "strength": "2mg", "dosage_form": "tablet", "manufacturer": "Sanofi", "therapeutic_category": "Antidiabetic", "prescription_required": True, "description": "Sulfonylurea for type 2 diabetes."},

    # Antihypertensives
    {"brand_name": "Telma 40", "generic_name": "Telmisartan", "composition": "Telmisartan", "strength": "40mg", "dosage_form": "tablet", "manufacturer": "Glenmark", "therapeutic_category": "Antihypertensive", "prescription_required": True, "description": "ARB for high blood pressure."},
    {"brand_name": "Telma H", "generic_name": "Telmisartan + Hydrochlorothiazide", "composition": "Telmisartan + Hydrochlorothiazide", "strength": "40mg+12.5mg", "dosage_form": "tablet", "manufacturer": "Glenmark", "therapeutic_category": "Antihypertensive", "prescription_required": True, "description": "Combination for hypertension."},
    {"brand_name": "Amlodipine 5", "generic_name": "Amlodipine", "composition": "Amlodipine", "strength": "5mg", "dosage_form": "tablet", "manufacturer": "Cipla", "therapeutic_category": "Antihypertensive", "prescription_required": True, "description": "Calcium channel blocker."},
    {"brand_name": "Atenolol 50", "generic_name": "Atenolol", "composition": "Atenolol", "strength": "50mg", "dosage_form": "tablet", "manufacturer": "IPCA Labs", "therapeutic_category": "Antihypertensive / Beta Blocker", "prescription_required": True, "description": "Beta blocker for hypertension and heart conditions."},
    {"brand_name": "Losartan 50", "generic_name": "Losartan", "composition": "Losartan", "strength": "50mg", "dosage_form": "tablet", "manufacturer": "Torrent", "therapeutic_category": "Antihypertensive", "prescription_required": True, "description": "ARB for hypertension."},
    {"brand_name": "Ramipril 5", "generic_name": "Ramipril", "composition": "Ramipril", "strength": "5mg", "dosage_form": "capsule", "manufacturer": "Sanofi", "therapeutic_category": "Antihypertensive / ACE Inhibitor", "prescription_required": True, "description": "ACE inhibitor for hypertension and heart failure."},
    {"brand_name": "Ecosprin 75", "generic_name": "Aspirin", "composition": "Aspirin", "strength": "75mg", "dosage_form": "tablet", "manufacturer": "USV", "therapeutic_category": "Antiplatelet", "prescription_required": True, "description": "Low-dose aspirin for cardiovascular prevention."},

    # Cholesterol
    {"brand_name": "Atorva 10", "generic_name": "Atorvastatin", "composition": "Atorvastatin", "strength": "10mg", "dosage_form": "tablet", "manufacturer": "Zydus", "therapeutic_category": "Lipid Lowering / Statin", "prescription_required": True, "description": "Statin for cholesterol management."},
    {"brand_name": "Atorva 20", "generic_name": "Atorvastatin", "composition": "Atorvastatin", "strength": "20mg", "dosage_form": "tablet", "manufacturer": "Zydus", "therapeutic_category": "Lipid Lowering / Statin", "prescription_required": True, "description": "Statin for cholesterol management."},
    {"brand_name": "Rosuvastatin 10", "generic_name": "Rosuvastatin", "composition": "Rosuvastatin", "strength": "10mg", "dosage_form": "tablet", "manufacturer": "Sun Pharma", "therapeutic_category": "Lipid Lowering / Statin", "prescription_required": True, "description": "Statin for high cholesterol."},

    # Respiratory / Cough & Cold
    {"brand_name": "Alex", "generic_name": "Phenylephrine + Chlorpheniramine + Dextromethorphan", "composition": "Phenylephrine + Chlorpheniramine + Dextromethorphan", "strength": "5mg+2mg+10mg", "dosage_form": "syrup", "manufacturer": "Glenmark", "therapeutic_category": "Cough & Cold", "prescription_required": False, "description": "Cough suppressant with decongestant."},
    {"brand_name": "Benadryl", "generic_name": "Diphenhydramine", "composition": "Diphenhydramine", "strength": "14.08mg/5ml", "dosage_form": "syrup", "manufacturer": "J&J", "therapeutic_category": "Cough & Cold", "prescription_required": False, "description": "Cough syrup and antihistamine."},
    {"brand_name": "Sinarest", "generic_name": "Paracetamol + Phenylephrine + Chlorpheniramine + Caffeine", "composition": "Paracetamol + Phenylephrine + Chlorpheniramine + Caffeine", "strength": "500mg+10mg+2mg+30mg", "dosage_form": "tablet", "manufacturer": "Centaur", "therapeutic_category": "Cough & Cold", "prescription_required": False, "description": "Cold and flu tablet."},
    {"brand_name": "Cheston Cold", "generic_name": "Cetirizine + Paracetamol + Phenylephrine", "composition": "Cetirizine + Paracetamol + Phenylephrine", "strength": "5mg+325mg+10mg", "dosage_form": "tablet", "manufacturer": "Cipla", "therapeutic_category": "Cough & Cold", "prescription_required": False, "description": "For cold, runny nose, and fever."},
    {"brand_name": "Asthalin", "generic_name": "Salbutamol", "composition": "Salbutamol", "strength": "100mcg", "dosage_form": "inhaler", "manufacturer": "Cipla", "therapeutic_category": "Bronchodilator", "prescription_required": True, "description": "Reliever inhaler for asthma and COPD."},
    {"brand_name": "Foracort 200", "generic_name": "Budesonide + Formoterol", "composition": "Budesonide + Formoterol", "strength": "200mcg+6mcg", "dosage_form": "inhaler", "manufacturer": "Cipla", "therapeutic_category": "Bronchodilator / Steroid", "prescription_required": True, "description": "Combination inhaler for asthma."},
    {"brand_name": "Seroflo 250", "generic_name": "Fluticasone + Salmeterol", "composition": "Fluticasone + Salmeterol", "strength": "250mcg+50mcg", "dosage_form": "inhaler", "manufacturer": "Cipla", "therapeutic_category": "Bronchodilator / Steroid", "prescription_required": True, "description": "Combination inhaler for asthma and COPD."},
    {"brand_name": "Deriphyllin", "generic_name": "Etofylline + Theophylline", "composition": "Etofylline + Theophylline", "strength": "77mg+23mg", "dosage_form": "tablet", "manufacturer": "Abbott", "therapeutic_category": "Bronchodilator", "prescription_required": True, "description": "For asthma and bronchospasm."},

    # Vitamins / Supplements
    {"brand_name": "Becosules", "generic_name": "B-Complex + Vitamin C", "composition": "B-Complex + Vitamin C", "strength": "multivitamin", "dosage_form": "capsule", "manufacturer": "Pfizer", "therapeutic_category": "Vitamin / Supplement", "prescription_required": False, "description": "B-complex vitamin supplement."},
    {"brand_name": "Shelcal 500", "generic_name": "Calcium + Vitamin D3", "composition": "Calcium Carbonate + Vitamin D3", "strength": "500mg+250IU", "dosage_form": "tablet", "manufacturer": "Torrent", "therapeutic_category": "Vitamin / Supplement", "prescription_required": False, "description": "Calcium and Vitamin D3 supplement."},
    {"brand_name": "Limcee", "generic_name": "Vitamin C", "composition": "Ascorbic Acid", "strength": "500mg", "dosage_form": "tablet", "manufacturer": "Abbott", "therapeutic_category": "Vitamin / Supplement", "prescription_required": False, "description": "Chewable Vitamin C supplement."},
    {"brand_name": "Zincovit", "generic_name": "Multivitamin + Multimineral", "composition": "Multivitamin + Zinc + Selenium", "strength": "multivitamin", "dosage_form": "tablet", "manufacturer": "Apex", "therapeutic_category": "Vitamin / Supplement", "prescription_required": False, "description": "Multivitamin and mineral supplement."},
    {"brand_name": "Supradyn", "generic_name": "Multivitamin", "composition": "Multivitamin + Multimineral", "strength": "multivitamin", "dosage_form": "tablet", "manufacturer": "Bayer", "therapeutic_category": "Vitamin / Supplement", "prescription_required": False, "description": "Complete daily multivitamin."},
    {"brand_name": "Ferrous Sulphate 200", "generic_name": "Ferrous Sulphate", "composition": "Ferrous Sulphate", "strength": "200mg", "dosage_form": "tablet", "manufacturer": "Sun Pharma", "therapeutic_category": "Iron Supplement", "prescription_required": False, "description": "Iron supplement for anaemia."},
    {"brand_name": "Dydroboon 10", "generic_name": "Dydrogesterone", "composition": "Dydrogesterone", "strength": "10mg", "dosage_form": "tablet", "manufacturer": "Abbott", "therapeutic_category": "Hormone", "prescription_required": True, "description": "Progesterone supplement."},

    # Dermatology
    {"brand_name": "Betnovate C", "generic_name": "Betamethasone + Clioquinol", "composition": "Betamethasone + Clioquinol", "strength": "0.1%+3%", "dosage_form": "cream", "manufacturer": "GSK", "therapeutic_category": "Dermatology / Steroid", "prescription_required": True, "description": "Topical steroid cream for skin conditions."},
    {"brand_name": "Candid B", "generic_name": "Clotrimazole + Beclometasone", "composition": "Clotrimazole + Beclometasone", "strength": "1%+0.025%", "dosage_form": "cream", "manufacturer": "Glenmark", "therapeutic_category": "Dermatology / Antifungal", "prescription_required": True, "description": "Antifungal cream with steroid."},
    {"brand_name": "Soframycin", "generic_name": "Framycetin", "composition": "Framycetin", "strength": "1%", "dosage_form": "cream", "manufacturer": "Sanofi", "therapeutic_category": "Dermatology / Antibiotic", "prescription_required": False, "description": "Topical antibiotic cream for wounds."},
    {"brand_name": "Clobetasol 0.05%", "generic_name": "Clobetasol", "composition": "Clobetasol Propionate", "strength": "0.05%", "dosage_form": "cream", "manufacturer": "Glenmark", "therapeutic_category": "Dermatology / Steroid", "prescription_required": True, "description": "Potent topical steroid."},
    {"brand_name": "T-Bact", "generic_name": "Mupirocin", "composition": "Mupirocin", "strength": "2%", "dosage_form": "cream", "manufacturer": "GSK", "therapeutic_category": "Dermatology / Antibiotic", "prescription_required": True, "description": "Topical antibiotic for skin infections."},

    # Ophthalmology
    {"brand_name": "Moxifloxacin Eye Drops", "generic_name": "Moxifloxacin", "composition": "Moxifloxacin", "strength": "0.5%", "dosage_form": "drops", "manufacturer": "Cipla", "therapeutic_category": "Ophthalmology", "prescription_required": True, "description": "Antibiotic eye drops."},
    {"brand_name": "Tears Naturale II", "generic_name": "Hydroxypropyl Methylcellulose + Dextran", "composition": "HPMC + Dextran 70", "strength": "0.3%+0.1%", "dosage_form": "drops", "manufacturer": "Alcon", "therapeutic_category": "Ophthalmology", "prescription_required": False, "description": "Artificial tears for dry eyes."},

    # Antifungal
    {"brand_name": "Fluconazole 150", "generic_name": "Fluconazole", "composition": "Fluconazole", "strength": "150mg", "dosage_form": "tablet", "manufacturer": "Cipla", "therapeutic_category": "Antifungal", "prescription_required": True, "description": "Systemic antifungal."},
    {"brand_name": "Terbinafine 250", "generic_name": "Terbinafine", "composition": "Terbinafine", "strength": "250mg", "dosage_form": "tablet", "manufacturer": "Dr. Reddy's", "therapeutic_category": "Antifungal", "prescription_required": True, "description": "Antifungal for nail and skin infections."},

    # Thyroid
    {"brand_name": "Thyronorm 50", "generic_name": "Levothyroxine", "composition": "Levothyroxine Sodium", "strength": "50mcg", "dosage_form": "tablet", "manufacturer": "Abbott", "therapeutic_category": "Thyroid", "prescription_required": True, "description": "Thyroid hormone replacement."},
    {"brand_name": "Thyronorm 100", "generic_name": "Levothyroxine", "composition": "Levothyroxine Sodium", "strength": "100mcg", "dosage_form": "tablet", "manufacturer": "Abbott", "therapeutic_category": "Thyroid", "prescription_required": True, "description": "Thyroid hormone replacement."},
    {"brand_name": "Eltroxin 100", "generic_name": "Levothyroxine", "composition": "Levothyroxine Sodium", "strength": "100mcg", "dosage_form": "tablet", "manufacturer": "GSK", "therapeutic_category": "Thyroid", "prescription_required": True, "description": "Thyroid hormone replacement."},

    # Antidepressants / CNS
    {"brand_name": "Escitalopram 10", "generic_name": "Escitalopram", "composition": "Escitalopram Oxalate", "strength": "10mg", "dosage_form": "tablet", "manufacturer": "Sun Pharma", "therapeutic_category": "Antidepressant / SSRI", "prescription_required": True, "description": "SSRI for depression and anxiety."},
    {"brand_name": "Clonazepam 0.5", "generic_name": "Clonazepam", "composition": "Clonazepam", "strength": "0.5mg", "dosage_form": "tablet", "manufacturer": "Sun Pharma", "therapeutic_category": "Anxiolytic / Benzodiazepine", "prescription_required": True, "description": "For anxiety and seizure disorders."},

    # Gastrointestinal  
    {"brand_name": "Duphalac", "generic_name": "Lactulose", "composition": "Lactulose", "strength": "10g/15ml", "dosage_form": "syrup", "manufacturer": "Abbott", "therapeutic_category": "Laxative", "prescription_required": False, "description": "Osmotic laxative for constipation."},
    {"brand_name": "Cremaffin", "generic_name": "Liquid Paraffin + Milk of Magnesia", "composition": "Liquid Paraffin + Milk of Magnesia + Sodium Picosulfate", "strength": "suspension", "dosage_form": "syrup", "manufacturer": "Abbott", "therapeutic_category": "Laxative", "prescription_required": False, "description": "Laxative emulsion."},
    {"brand_name": "ORS", "generic_name": "Oral Rehydration Salts", "composition": "Sodium Chloride + Potassium Chloride + Sodium Citrate + Dextrose", "strength": "packet", "dosage_form": "other", "manufacturer": "Various", "therapeutic_category": "Rehydration", "prescription_required": False, "description": "Oral rehydration solution for diarrhoea."},
    {"brand_name": "Racecadotril 100", "generic_name": "Racecadotril", "composition": "Racecadotril", "strength": "100mg", "dosage_form": "capsule", "manufacturer": "Abbott", "therapeutic_category": "Antidiarrhoeal", "prescription_required": True, "description": "Antisecretory antidiarrhoeal."},

    # Muscle Relaxants
    {"brand_name": "Myospaz Forte", "generic_name": "Chlorzoxazone + Diclofenac + Paracetamol", "composition": "Chlorzoxazone + Diclofenac + Paracetamol", "strength": "250mg+50mg+325mg", "dosage_form": "tablet", "manufacturer": "USV", "therapeutic_category": "Muscle Relaxant / Analgesic", "prescription_required": True, "description": "Muscle relaxant with anti-inflammatory."},
    {"brand_name": "Thiocolchicoside 4", "generic_name": "Thiocolchicoside", "composition": "Thiocolchicoside", "strength": "4mg", "dosage_form": "capsule", "manufacturer": "Sanofi", "therapeutic_category": "Muscle Relaxant", "prescription_required": True, "description": "Muscle relaxant for acute spasm."},

    # Antiemetic  
    {"brand_name": "Emeset 4", "generic_name": "Ondansetron", "composition": "Ondansetron", "strength": "4mg", "dosage_form": "tablet", "manufacturer": "Cipla", "therapeutic_category": "Antiemetic", "prescription_required": True, "description": "For nausea and vomiting."},

    # Corticosteroids
    {"brand_name": "Wysolone 5", "generic_name": "Prednisolone", "composition": "Prednisolone", "strength": "5mg", "dosage_form": "tablet", "manufacturer": "Pfizer", "therapeutic_category": "Corticosteroid", "prescription_required": True, "description": "Systemic corticosteroid."},
    {"brand_name": "Deflazacort 6", "generic_name": "Deflazacort", "composition": "Deflazacort", "strength": "6mg", "dosage_form": "tablet", "manufacturer": "Zydus", "therapeutic_category": "Corticosteroid", "prescription_required": True, "description": "Corticosteroid with fewer side effects than prednisolone."},

    # ENT
    {"brand_name": "Otrivin", "generic_name": "Xylometazoline", "composition": "Xylometazoline", "strength": "0.1%", "dosage_form": "drops", "manufacturer": "Novartis", "therapeutic_category": "Nasal Decongestant", "prescription_required": False, "description": "Nasal decongestant spray."},
    {"brand_name": "Nasivion", "generic_name": "Oxymetazoline", "composition": "Oxymetazoline", "strength": "0.05%", "dosage_form": "drops", "manufacturer": "P&G", "therapeutic_category": "Nasal Decongestant", "prescription_required": False, "description": "Nasal decongestant."},

    # Urology
    {"brand_name": "Tamsulosin 0.4", "generic_name": "Tamsulosin", "composition": "Tamsulosin", "strength": "0.4mg", "dosage_form": "capsule", "manufacturer": "Sun Pharma", "therapeutic_category": "Urology", "prescription_required": True, "description": "Alpha-blocker for BPH."},

    # Emergency / First Aid
    {"brand_name": "ORS Zinc", "generic_name": "ORS + Zinc", "composition": "ORS + Zinc Sulphate", "strength": "20mg", "dosage_form": "tablet", "manufacturer": "Various", "therapeutic_category": "Rehydration", "prescription_required": False, "description": "Zinc supplement for diarrhoea in children."},
    {"brand_name": "Betadine", "generic_name": "Povidone Iodine", "composition": "Povidone Iodine", "strength": "5%", "dosage_form": "other", "manufacturer": "Win-Medicare", "therapeutic_category": "Antiseptic", "prescription_required": False, "description": "Antiseptic solution for wounds."},
    {"brand_name": "Band-Aid Antiseptic", "generic_name": "Antiseptic Cream", "composition": "Cetrimide + Lidocaine", "strength": "0.5%+0.5%", "dosage_form": "cream", "manufacturer": "J&J", "therapeutic_category": "Antiseptic", "prescription_required": False, "description": "First-aid antiseptic cream."},

    # More to reach 100+
    {"brand_name": "Gudcef CV 200", "generic_name": "Cefpodoxime + Clavulanic Acid", "composition": "Cefpodoxime + Clavulanic Acid", "strength": "200mg+125mg", "dosage_form": "tablet", "manufacturer": "Alkem", "therapeutic_category": "Antibiotic", "prescription_required": True, "description": "Third-gen cephalosporin combination."},
    {"brand_name": "Taxim O 200", "generic_name": "Cefixime", "composition": "Cefixime", "strength": "200mg", "dosage_form": "tablet", "manufacturer": "Alkem", "therapeutic_category": "Antibiotic", "prescription_required": True, "description": "Third-gen oral cephalosporin."},
    {"brand_name": "Levofloxacin 500", "generic_name": "Levofloxacin", "composition": "Levofloxacin", "strength": "500mg", "dosage_form": "tablet", "manufacturer": "Cipla", "therapeutic_category": "Antibiotic", "prescription_required": True, "description": "Fluoroquinolone antibiotic."},
    {"brand_name": "PCM 650", "generic_name": "Paracetamol", "composition": "Paracetamol", "strength": "650mg", "dosage_form": "tablet", "manufacturer": "Mankind", "therapeutic_category": "Analgesic / Antipyretic", "prescription_required": False, "description": "Paracetamol for fever and pain."},
    {"brand_name": "Aciloc 150", "generic_name": "Ranitidine", "composition": "Ranitidine", "strength": "150mg", "dosage_form": "tablet", "manufacturer": "Cadila", "therapeutic_category": "Antacid / H2 Blocker", "prescription_required": False, "description": "H2 receptor antagonist."},
    {"brand_name": "Pan D", "generic_name": "Pantoprazole + Domperidone", "composition": "Pantoprazole + Domperidone", "strength": "40mg+10mg", "dosage_form": "capsule", "manufacturer": "Alkem", "therapeutic_category": "Antacid / PPI", "prescription_required": True, "description": "PPI with prokinetic."},
    {"brand_name": "Volini Gel", "generic_name": "Diclofenac", "composition": "Diclofenac Diethylamine", "strength": "1.16%", "dosage_form": "cream", "manufacturer": "Sun Pharma", "therapeutic_category": "Topical Analgesic", "prescription_required": False, "description": "Topical pain relief gel."},
    {"brand_name": "Moov", "generic_name": "Diclofenac + Methyl Salicylate", "composition": "Diclofenac + Linseed Oil + Turpentine Oil", "strength": "topical", "dosage_form": "cream", "manufacturer": "Reckitt", "therapeutic_category": "Topical Analgesic", "prescription_required": False, "description": "Pain relief cream for muscle pain."},
    {"brand_name": "Ibuprofen 400", "generic_name": "Ibuprofen", "composition": "Ibuprofen", "strength": "400mg", "dosage_form": "tablet", "manufacturer": "Cipla", "therapeutic_category": "Analgesic / Anti-inflammatory", "prescription_required": False, "description": "NSAID for pain and inflammation."},
]

# ---------------------------------------------------------------------------
# 10 Pharmacies (Pune, India area)
# ---------------------------------------------------------------------------
PHARMACIES = [
    {"name": "Apollo Pharmacy - Kothrud", "address": "Shop 5, Paud Road, Kothrud, Pune 411038", "lat": 18.5074, "lng": 73.8077, "phone": "+91-20-25381001"},
    {"name": "MedPlus - Baner", "address": "Baner Road, near D-Mart, Baner, Pune 411045", "lat": 18.5590, "lng": 73.7868, "phone": "+91-20-27292002"},
    {"name": "Netmeds Pharmacy - Hinjewadi", "address": "Phase 1, Hinjewadi IT Park, Pune 411057", "lat": 18.5912, "lng": 73.7380, "phone": "+91-20-22934003"},
    {"name": "Wellness Forever - Viman Nagar", "address": "Datta Mandir Road, Viman Nagar, Pune 411014", "lat": 18.5679, "lng": 73.9143, "phone": "+91-20-26631004"},
    {"name": "Noble Chemist - Deccan", "address": "FC Road, Deccan Gymkhana, Pune 411004", "lat": 18.5186, "lng": 73.8401, "phone": "+91-20-25673005"},
    {"name": "Sai Medical - Hadapsar", "address": "Magarpatta Road, Hadapsar, Pune 411028", "lat": 18.5089, "lng": 73.9260, "phone": "+91-20-26870006"},
    {"name": "Pharma Point - Aundh", "address": "Aundh Road, ITI Signal, Pune 411007", "lat": 18.5580, "lng": 73.8073, "phone": "+91-20-25884007"},
    {"name": "LifeCare Pharmacy - Wakad", "address": "Datta Mandir Chowk, Wakad, Pune 411057", "lat": 18.5990, "lng": 73.7631, "phone": "+91-20-27251008"},
    {"name": "City Drug House - Camp", "address": "East Street, Camp, Pune 411001", "lat": 18.5145, "lng": 73.8778, "phone": "+91-20-26334009"},
    {"name": "Medicare Pharmacy - Koregaon Park", "address": "Lane 6, Koregaon Park, Pune 411001", "lat": 18.5362, "lng": 73.8938, "phone": "+91-20-26150010"},
]


class Command(BaseCommand):
    help = (
        "Seed comprehensive demo data: users, 100+ medicines, 10 pharmacies, "
        "inventory records, 30-90 days of inventory history, and alternative candidates. "
        "All records are labelled is_demo_data=True. Safe to run multiple times."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing demo data before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from medicines.models import Medicine
        from pharmacies.models import Pharmacy
        from inventory.models import Inventory, InventoryHistory
        from alternatives.models import AlternativeCandidate

        # Reproducible demo dataset: fixed seed.
        random.seed(1337)

        if options["reset"]:
            self.stdout.write(self.style.WARNING("Deleting existing demo data..."))
            AlternativeCandidate.objects.filter(
                medicine__is_demo_data=True
            ).delete()
            InventoryHistory.objects.filter(is_demo_data=True).delete()
            Inventory.objects.filter(is_demo_data=True).delete()
            Pharmacy.objects.filter(is_demo_data=True).delete()
            Medicine.objects.filter(is_demo_data=True).delete()
            User.objects.filter(email__endswith="@smartmed.demo").delete()
            self.stdout.write(self.style.SUCCESS("  Demo data cleared."))

        # 1. Users
        self.stdout.write(self.style.MIGRATE_HEADING("\n--- Seeding Users ---"))
        users = self._seed_users()

        # 2. Medicines
        self.stdout.write(self.style.MIGRATE_HEADING("\n--- Seeding Medicines ---"))
        medicines = self._seed_medicines()

        # 3. Pharmacies
        self.stdout.write(self.style.MIGRATE_HEADING("\n--- Seeding Pharmacies ---"))
        pharmacies = self._seed_pharmacies(users)

        # 4. Inventory + History
        self.stdout.write(self.style.MIGRATE_HEADING("\n--- Seeding Inventory & History ---"))
        self._seed_inventory(pharmacies, medicines)

        # 5. Alternative candidates
        self.stdout.write(self.style.MIGRATE_HEADING("\n--- Seeding Alternative Candidates ---"))
        self._seed_alternatives(medicines)

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Demo data seeded successfully."
            f"\nAll demo accounts use password: {DEMO_PASSWORD}"
        ))

    def _seed_users(self):
        created = 0
        users = {}
        for spec in DEMO_USERS:
            user, was_created = User.objects.get_or_create(
                email=spec["email"],
                defaults={
                    "name": spec["name"],
                    "role": spec["role"],
                    "is_staff": spec.get("is_staff", False),
                    "is_superuser": spec.get("is_superuser", False),
                },
            )
            if was_created:
                user.set_password(DEMO_PASSWORD)
                user.save()
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  Created: {spec['email']} [{spec['role']}]"))
            else:
                self.stdout.write(f"  Exists: {spec['email']}")
            users[spec["role"]] = user
        self.stdout.write(f"  {created} user(s) created.")
        return users

    def _seed_medicines(self):
        from medicines.models import Medicine

        created = 0
        medicines = []
        for spec in MEDICINES:
            med, was_created = Medicine.objects.get_or_create(
                brand_name=spec["brand_name"],
                strength=spec["strength"],
                manufacturer=spec["manufacturer"],
                defaults={
                    "generic_name": spec["generic_name"],
                    "composition": spec["composition"],
                    "dosage_form": spec["dosage_form"],
                    "therapeutic_category": spec["therapeutic_category"],
                    "prescription_required": spec["prescription_required"],
                    "description": spec["description"],
                    "is_demo_data": True,
                },
            )
            if was_created:
                created += 1
            medicines.append(med)

        self.stdout.write(self.style.SUCCESS(f"  {created} medicine(s) created ({len(medicines)} total in catalog)."))
        return medicines

    def _seed_pharmacies(self, users):
        from pharmacies.models import Pharmacy

        # Get pharmacy owner users
        pharmacy_owners = list(User.objects.filter(
            email__in=["pharmacy1@smartmed.demo", "pharmacy2@smartmed.demo"]
        ))

        created = 0
        pharmacies = []
        for i, spec in enumerate(PHARMACIES):
            owner = pharmacy_owners[i % len(pharmacy_owners)]
            pharmacy, was_created = Pharmacy.objects.get_or_create(
                name=spec["name"],
                defaults={
                    "owner": owner,
                    "address": spec["address"],
                    "latitude": spec["lat"],
                    "longitude": spec["lng"],
                    "phone": spec["phone"],
                    "opening_hours": {
                        "mon": ["09:00", "21:00"],
                        "tue": ["09:00", "21:00"],
                        "wed": ["09:00", "21:00"],
                        "thu": ["09:00", "21:00"],
                        "fri": ["09:00", "21:00"],
                        "sat": ["09:00", "18:00"],
                        "sun": ["10:00", "14:00"] if i % 3 != 0 else None,
                    },
                    "verification_status": "verified" if i < 7 else "pending",
                    "is_demo_data": True,
                },
            )
            if was_created:
                created += 1
            pharmacies.append(pharmacy)

        self.stdout.write(self.style.SUCCESS(f"  {created} pharmacy(ies) created ({len(pharmacies)} total)."))
        return pharmacies

    def _seed_inventory(self, pharmacies, medicines):
        from inventory.models import Inventory, InventoryHistory

        now = timezone.now()
        total_inv = 0
        total_hist = 0
        therapeutic_weights = {
            "Analgesic / Antipyretic": (8, 18),
            "Antibiotic": (4, 10),
            "Antacid / PPI": (5, 11),
            "Antihistamine": (3, 7),
            "Antidiabetic": (2, 6),
            "Antihypertensive": (2, 6),
            "Vitamin / Supplement": (1, 4),
        }

        for pharmacy in pharmacies:
            # Each pharmacy stocks 40-80% of medicines
            stock_fraction = random.uniform(0.4, 0.8)
            stocked = random.sample(medicines, k=int(len(medicines) * stock_fraction))

            for medicine in stocked:
                # Random initial quantity and price
                base_quantity = random.randint(15, 220)
                price = Decimal(str(round(random.uniform(5.0, 500.0), 2)))

                inv, created = Inventory.objects.get_or_create(
                    pharmacy=pharmacy,
                    medicine=medicine,
                    defaults={
                        "quantity": base_quantity,
                        "price": price,
                        "batch_number": f"DEMO-{random.randint(100000, 999999)}",
                        "is_demo_data": True,
                    },
                )
                if created:
                    total_inv += 1
                elif inv.price is None:
                    inv.price = price

                existing_history_count = InventoryHistory.objects.filter(
                    pharmacy=pharmacy,
                    medicine=medicine,
                ).count()
                if existing_history_count >= 45:
                    continue

                # Generate 45-120 days of historical data
                history_days = random.randint(45, 120)
                history_records = []
                quantity = max(base_quantity + random.randint(40, 180), 20)
                category = medicine.therapeutic_category or ""
                demand_low, demand_high = therapeutic_weights.get(category, (2, 8))
                restock_every = random.randint(8, 15)

                for day_offset in range(history_days, 0, -1):
                    ts = now - timedelta(days=day_offset)
                    ts = ts.replace(
                        hour=random.randint(8, 20),
                        minute=random.randint(0, 59),
                        second=0,
                        microsecond=0,
                    )

                    base_demand = random.randint(demand_low, demand_high)
                    if "Paracetamol" in medicine.composition:
                        base_demand += random.randint(2, 5)
                    if medicine.prescription_required:
                        base_demand = max(1, base_demand - 1)

                    if ts.weekday() == 6:  # Sunday
                        daily_demand = max(0, base_demand - random.randint(2, 4))
                    elif ts.weekday() == 5:  # Saturday
                        daily_demand = base_demand + random.randint(1, 4)
                    else:
                        daily_demand = base_demand + random.randint(0, 3)

                    quantity = max(0, quantity - daily_demand)

                    if quantity < 12 or (day_offset % restock_every == 0):
                        restock = random.randint(35, 160)
                        quantity += restock

                    history_records.append(
                        InventoryHistory(
                            pharmacy=pharmacy,
                            medicine=medicine,
                            quantity=quantity,
                            timestamp=ts,
                            is_demo_data=True,
                        )
                    )

                InventoryHistory.objects.bulk_create(history_records)
                total_hist += len(history_records)

                # Update current inventory to match latest history
                inv.quantity = quantity
                inv.is_demo_data = True
                inv.save()

        self.stdout.write(self.style.SUCCESS(
            f"  {total_inv} inventory record(s) created."
            f"\n  {total_hist} inventory history record(s) created."
        ))

    def _seed_alternatives(self, medicines):
        from alternatives.models import AlternativeCandidate
        from medicines.models import normalize_text

        created = 0
        # Group medicines by composition (normalized)
        composition_groups = {}
        for med in medicines:
            key = normalize_text(med.composition)
            if key not in composition_groups:
                composition_groups[key] = []
            composition_groups[key].append(med)

        for key, group in composition_groups.items():
            if len(group) < 2:
                continue
            # Create alternative candidates within the group
            for i, med_a in enumerate(group):
                for med_b in group[i + 1:]:
                    # Calculate similarity based on shared attributes
                    score = 0.7  # base score for same composition
                    if normalize_text(med_a.strength) == normalize_text(med_b.strength):
                        score += 0.15
                    if med_a.dosage_form == med_b.dosage_form:
                        score += 0.1
                    if normalize_text(med_a.therapeutic_category) == normalize_text(med_b.therapeutic_category):
                        score += 0.05
                    score = min(score, 1.0)

                    for m1, m2 in [(med_a, med_b), (med_b, med_a)]:
                        _, was_created = AlternativeCandidate.objects.get_or_create(
                            medicine=m1,
                            candidate_medicine=m2,
                            defaults={
                                "matching_basis": "combined",
                                "confidence_score": round(score, 2),
                                "verification_status": random.choice(["pending", "pending", "approved"]),
                            },
                        )
                        if was_created:
                            created += 1

        self.stdout.write(self.style.SUCCESS(f"  {created} alternative candidate(s) created."))
