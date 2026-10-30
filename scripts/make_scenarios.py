"""Write the 40 synthetic eval scenarios to data/scenarios/*.json.

All names, accounts and stories are invented. Drafted with an LLM, then reviewed by hand;
committed before any rule or weight tuning. 24 scam (5 coached) + 16 genuine, 20 dev / 20 test.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "scenarios"

GENUINE = {"Q2": "no", "Q3": "yes", "Q4": "no", "Q5": "no", "Q6": "no", "Q7": "no", "Q8": "no", "Q9": "no",
           "Q10": "yes"}
SCAM = {"Q2": "yes", "Q3": "no", "Q4": "no", "Q5": "no", "Q6": "no", "Q7": "no", "Q8": "no", "Q9": "no",
        "Q10": "yes"}


def txn(age, avg, max_single, amount, kind, new=True, call=False, companion=False, notes="", payee=""):
    return {"customer_age": age, "avg_monthly_debit_inr": avg, "max_single_debit_inr_12m": max_single,
            "txn_amount_inr": amount, "txn_type": kind, "beneficiary_is_new": new,
            "customer_on_call_at_counter": call, "accompanied_by_unknown_person": companion,
            "payee_reference": payee or "SAMPLE-PAYEE", "staff_notes": notes}


def ans(q1, base, **over):
    out = {"Q1": {"detail": q1}}
    for qid in [f"Q{i}" for i in range(2, 11)]:
        v = over.get(qid, base[qid])
        choice, detail = (v if isinstance(v, tuple) else (v, ""))
        out[qid] = {"choice": choice, "detail": detail}
    return out


def sc(id, title, split, lang, scam_type, t, a, coached=False, notice=""):
    return {"id": id, "title": title, "split": split, "language": lang,
            "label": {"is_scam": scam_type != "genuine", "scam_type": None if scam_type == "genuine" else scam_type,
                      "coached": coached},
            "transaction": t, "answers": a, "notice_text": notice}


S = []

# --- digital arrest (10: 5 dev, 5 test; coached: da_03, da_08, da_10) ---------------------------
S.append(sc("da_01", "Senior citizen, 'CBI' video call, RBI safe account (demo 1)", "dev", "hi", "digital_arrest",
    txn(72, 40000, 150000, 1800000, "RTGS", call=True, payee="SAMPLE-ACCT-000011112222",
        notes="Customer anxious, keeps looking at phone, video call open"),
    ans("मेरे खाते की जांच चल रही है, सीबीआई वालों ने कहा है कि यह पैसा आरबीआई के सुरक्षित खाते में डालना है", SCAM,
        Q2=("yes", "हाँ, सीबीआई के अधिकारी ने कहा कि आज ही भेजना है"),
        Q3=("no", "नहीं, उन्होंने खाता नंबर दिया है"),
        Q4=("yes", "हाँ, मुंबई पुलिस और सीबीआई से फोन आया था, कहा मेरे आधार से मनी लॉन्ड्रिंग हुई है"),
        Q5=("yes", "हाँ, बोले किसी को मत बताना, बेटे को भी नहीं"),
        Q6=("yes", "हाँ, दो दिन से वीडियो कॉल पर हूँ, कैमरा चालू रखने को कहा है"),
        Q7=("yes", "हाँ, बोले जांच के बाद पैसा वापस मिल जाएगा"),
        Q8=("yes", "हाँ, बोले डिजिटल अरेस्ट है, पैसे नहीं भेजे तो गिरफ्तार कर लेंगे"),
        Q9=("yes", "व्हाट्सऐप पर एक वारंट भेजा था"),
        Q10=("no", "नहीं, उन्होंने मना किया है"))))

S.append(sc("da_02", "Retired teacher, parcel with drugs, crime branch", "dev", "en", "digital_arrest",
    txn(68, 35000, 100000, 950000, "RTGS", call=True),
    ans("The officer from Mumbai Crime Branch said my money must be verified, so I am transferring it to the "
        "account they gave.", SCAM,
        Q2=("yes", "Officer Sharma from the Crime Branch told me to transfer it today."),
        Q3=("no", "No, it is a government verification account."),
        Q4=("yes", "Yes, a courier company first, then the police. They said a parcel in my name had drugs and "
                   "five passports."),
        Q5=("yes", "They told me this is a confidential investigation and I must not tell my children."),
        Q6=("yes", "Yes, on video since this morning."),
        Q7=("yes", "They said it will be refunded after the investigation is over."),
        Q8=("yes", "They said a warrant is issued and I will be arrested tonight."),
        Q9=("yes", "They sent an arrest warrant with a court stamp on WhatsApp."),
        Q10=("no", "They said if I call anyone the case gets worse."))))

S.append(sc("da_03", "Coached: 'advance to builder', on phone with 'nephew'", "dev", "hinglish", "digital_arrest",
    txn(74, 50000, 200000, 2200000, "RTGS", call=True,
        notes="Customer on phone with earphones, says it is his nephew"),
    ans("Ghar ke liye builder ko advance de raha hoon", GENUINE,
        Q3=("yes", "haan builder ko jaanta hoon"),
        Q6=("no", "nahi, bhatija hai phone par"),
        Q10=("no", "abhi zaroorat nahi, main khud kar lunga")), coached=True))

S.append(sc("da_04", "Customs 'fine' in cash for a seized parcel", "dev", "hi", "digital_arrest",
    txn(65, 30000, 80000, 600000, "CASH", new=False),
    ans("कस्टम विभाग वालों को जुर्माना देना है, मेरे नाम का पार्सल पकड़ा गया है", SCAM,
        Q2=("yes", "हाँ, कस्टम ऑफिसर ने कहा नकद लाकर दो"),
        Q4=("yes", "हाँ, कस्टम और फिर पुलिस"),
        Q5=("yes", "बोले घर पर मत बताना"),
        Q6=("no", "अभी नहीं, बाद में फोन करेंगे"),
        Q7=("unsure", "पता नहीं"),
        Q8=("yes", "बोले जुर्माना नहीं दिया तो जेल हो जाएगी"))))

S.append(sc("da_05", "FD break for 'RBI checking', Aadhaar laundering claim", "dev", "en", "digital_arrest",
    txn(61, 45000, 150000, 1400000, "FD_BREAK", call=True),
    ans("I need to break my FD and send it to the RBI account for checking my funds.", SCAM,
        Q2=("yes", "The ED officer told me."),
        Q4=("yes", "Enforcement Directorate. They said my Aadhaar was used to open an account for money laundering."),
        Q5="yes",
        Q6=("yes", "Yes, he is listening on video call."),
        Q7=("yes", "He said after RBI checks it, the money comes back in 2 days."),
        Q8="yes", Q10="no")))

S.append(sc("da_06", "Supreme Court 'bail deposit' on video call", "test", "hi", "digital_arrest",
    txn(70, 25000, 90000, 1100000, "RTGS", call=True),
    ans("मुझे सुप्रीम कोर्ट में जमानत के लिए पैसा जमा करना है", SCAM,
        Q2=("yes", "हाँ, जज साहब ने कहा"),
        Q4=("yes", "हाँ, सुप्रीम कोर्ट और सीबीआई"),
        Q5=("yes", "हाँ, किसी को भी नहीं बताना है"),
        Q6=("yes", "हाँ, वीडियो कॉल चल रही है"),
        Q7=("yes", "हाँ, केस खत्म होने पर लौटा देंगे"),
        Q8=("yes", "हाँ, कहा घर से बाहर नहीं जा सकते, डिजिटल अरेस्ट है"),
        Q9=("yes", "हाँ, कोर्ट का ऑर्डर आया"),
        Q10="no")))

S.append(sc("da_07", "TRAI SIM misuse, 'safe account', call ended", "test", "en", "digital_arrest",
    txn(66, 60000, 200000, 800000, "NEFT"),
    ans("Transfer to a safe account as told by the TRAI officer, my SIM was used in illegal activity.", SCAM,
        Q4=("yes", "TRAI and then Mumbai police"),
        Q5=("yes", "They said not to tell the bank why"),
        Q6=("no", "They told me to call back after the transfer"),
        Q7="yes",
        Q8=("yes", "Mumbai police said arrest warrant is ready"),
        Q10=("unsure", "My son is busy"))))

S.append(sc("da_08", "Coached: 'son's business', son can't be called", "test", "hi", "digital_arrest",
    txn(69, 40000, 120000, 1600000, "RTGS", call=True,
        notes="Customer whispering on phone, insists it is urgent"),
    ans("बेटे के बिज़नेस के लिए पैसा भेज रही हूँ", GENUINE,
        Q3=("yes", "हाँ, जानती हूँ"),
        Q6=("no", "नहीं"),
        Q10=("no", "बेटा अभी मीटिंग में है, फोन मत करिए")), coached=True))

S.append(sc("da_09", "CBI/ED 'account verification', camera on", "test", "hinglish", "digital_arrest",
    txn(63, 55000, 150000, 750000, "RTGS", call=True),
    ans("CBI wale bole account verify karna hai, paisa unke khate mein dalna hai", SCAM,
        Q2=("yes", "CBI officer ne bola aaj hi bhejna hai"),
        Q4=("yes", "haan CBI aur ED dono"),
        Q5=("yes", "bole kisi ko mat batana warna family bhi fasegi"),
        Q6=("yes", "haan video call pe hoon, camera on rakhne bola"),
        Q7=("yes", "bole verification ke baad paisa wapas aa jayega"),
        Q8=("yes", "bole digital arrest hai"),
        Q10="no")))

S.append(sc("da_10", "Coached: 'buying a plot', unknown man answers for him", "test", "en", "digital_arrest",
    txn(77, 60000, 300000, 2500000, "RTGS", companion=True,
        notes="Young man accompanying the customer answers for him, says he is from the bank's head office"),
    ans("Buying a plot of land.", GENUINE,
        Q2=("no", "My own decision"),
        Q3=("yes", "Yes, the seller is my friend's relative"),
        Q10=("no", "Not needed")), coached=True))

# --- investment (5: 3 dev, 2 test; coached: inv_02) ----------------------------------------------
S.append(sc("inv_01", "IPO allotment via WhatsApp group trading app (demo 2)", "dev", "en", "investment",
    txn(58, 70000, 200000, 500000, "NEFT"),
    ans("Investing in an IPO allotment through the trading app my WhatsApp group recommended.", SCAM,
        Q2=("yes", "The group admin told me to add funds today to get the allotment"),
        Q3=("no", "It is the company account shown in the app"),
        Q5=("yes", "The mentor said banks discourage these investments, so don't tell the bank staff"))))

S.append(sc("inv_02", "Coached: 'friend's business', trading app on screen", "dev", "hinglish", "investment",
    txn(52, 80000, 300000, 900000, "RTGS",
        notes="Customer showed a trading app screen with 300% profit while waiting"),
    ans("Paise apne dost ke business mein laga raha hoon", GENUINE,
        Q3=("yes", "haan dost hai"),
        Q10=("yes", "haan, kar lijiye")), coached=True))

S.append(sc("inv_03", "Telegram group 'money doubles' trading app", "dev", "hi", "investment",
    txn(60, 40000, 100000, 300000, "NEFT"),
    ans("टेलीग्राम ग्रुप में बताया कि पैसा डबल हो जाएगा, ट्रेडिंग ऐप में डालना है", SCAM,
        Q2=("yes", "हाँ, ग्रुप के सर ने कहा"),
        Q7=("yes", "हाँ, कहा प्रॉफिट के साथ पैसा वापस आ जाएगा"))))

S.append(sc("inv_04", "Advisory promising 4% weekly, 'SEBI certificate'", "test", "en", "investment",
    txn(45, 100000, 400000, 1200000, "RTGS"),
    ans("Guaranteed 4% weekly returns from a stock market advisory, they need margin money.", SCAM,
        Q2=("yes", "The advisor said slots close tonight"),
        Q9=("yes", "They sent a SEBI registration certificate on WhatsApp"))))

S.append(sc("inv_05", "WhatsApp 'sir' on the line, IPO will triple", "test", "hinglish", "investment",
    txn(67, 30000, 100000, 600000, "RTGS", call=True),
    ans("WhatsApp group ke sir bole IPO mein paisa lagao, triple ho jayega", SCAM,
        Q5=("yes", "bole bete ko mat batana, wo rok dega"),
        Q6=("yes", "haan, sir line par hain"),
        Q10=("unsure", "pata nahi"))))

# --- KYC or account block (4: 2 dev, 2 test) -------------------------------------------------------
S.append(sc("kyc_01", "'KYC cell' says account frozen today, move balance", "dev", "en", "kyc_or_account_block",
    txn(64, 30000, 60000, 250000, "NEFT", call=True),
    ans("The bank's KYC department said my account will be frozen today unless I move the balance to a "
        "temporary account.", SCAM,
        Q4=("yes", "They said they are from RBI KYC cell"),
        Q5=("yes", "They said branch staff are not authorised to know"),
        Q6="yes",
        Q7=("yes", "They said it will be returned once KYC is updated"),
        Q8=("yes", "They said the account will be frozen today"),
        Q9=("yes", "An SMS with a link to update PAN"),
        Q10="no")))

S.append(sc("kyc_02", "Phone 'bank officer': KYC not updated, account will close", "dev", "hi",
    "kyc_or_account_block",
    txn(71, 20000, 50000, 180000, "NEFT"),
    ans("बैंक वालों ने फोन पर कहा केवाईसी अपडेट नहीं हुई तो खाता बंद हो जाएगा, इसलिए पैसे दूसरे खाते में डाल रहा हूँ",
        SCAM,
        Q2=("yes", "हाँ, बैंक के अधिकारी ने कहा"),
        Q7=("yes", "हाँ, कहा अपडेट के बाद वापस आ जाएगा"),
        Q8=("yes", "कहा आज खाता फ्रीज़ हो जाएगा"))))

S.append(sc("kyc_03", "'Customer care': PAN not linked, safe account", "test", "hinglish",
    "kyc_or_account_block",
    txn(59, 25000, 40000, 95000, "IMPS", call=True),
    ans("Customer care wale bole PAN link nahi hai, account block ho jayega, isliye safe account mein transfer",
        SCAM,
        Q6=("yes", "haan wo line par hain"),
        Q7="yes",
        Q8=("yes", "aaj account freeze ho jayega bole"))))

S.append(sc("kyc_04", "SIM 're-verification fee' in cash to an agent", "test", "en", "kyc_or_account_block",
    txn(62, 30000, 50000, 60000, "CASH", new=False),
    ans("The SIM card company said my SIM will be deactivated and my bank account frozen unless I pay a "
        "re-verification fee in cash to their agent.", SCAM,
        Q8=("yes", "They said the account would be frozen tonight"))))

# --- relative in trouble (3: 1 dev, 2 test; coached: rel_03) ---------------------------------------
S.append(sc("rel_01", "Grandson 'arrested after accident', inspector on call", "dev", "hi", "relative_in_trouble",
    txn(75, 30000, 100000, 350000, "NEFT", call=True),
    ans("पोते का एक्सीडेंट हो गया है, पुलिस ने पकड़ लिया है, छुड़ाने के लिए पैसे भेजने हैं", SCAM,
        Q2=("yes", "एक पुलिस इंस्पेक्टर ने फोन किया"),
        Q4="yes",
        Q5=("yes", "कहा बेटे को मत बताना, वो गुस्सा होगा"),
        Q6="yes",
        Q8=("yes", "कहा आज नहीं भेजा तो पोता जेल जाएगा"),
        Q10="no")))

S.append(sc("rel_02", "Son 'in an accident in Dubai', hospital deposit", "test", "en", "relative_in_trouble",
    txn(68, 40000, 70000, 200000, "IMPS"),
    ans("My son called from Dubai, he was in an accident and the hospital needs a deposit.", SCAM,
        Q2=("yes", "Someone from the hospital called from a new number"),
        Q3=("no", "It is the hospital's account they said"),
        Q5=("unsure", "He said don't worry the family"),
        Q10=("no", "His phone is switched off"))))

S.append(sc("rel_03", "Coached: 'nephew's college fees', crying on phone", "test", "hinglish",
    "relative_in_trouble",
    txn(72, 25000, 60000, 150000, "NEFT", call=True, notes="Customer crying, on phone"),
    ans("Bhatije ki college fees hai", GENUINE,
        Q3=("yes", "haan"),
        Q6=("no", "nahi"),
        Q10=("no", "nahi, zaroorat nahi")), coached=True))

# --- lottery or refund (2: 1 dev, 1 test) ----------------------------------------------------------
S.append(sc("lot_01", "Quiz-show 'prize' processing fee", "dev", "en", "lottery_or_refund",
    txn(66, 20000, 40000, 85000, "NEFT"),
    ans("Processing fee and GST to release my TV quiz show lottery prize of 25 lakh.", SCAM,
        Q2=("yes", "The prize office told me to pay the fee today"),
        Q5=("yes", "They said keep it secret from relatives until the prize is released"),
        Q7=("yes", "The fee will be refunded with the prize"),
        Q9=("yes", "A prize certificate on WhatsApp"))))

S.append(sc("lot_02", "'Income tax refund' processing fee", "test", "hi", "lottery_or_refund",
    txn(63, 35000, 80000, 120000, "NEFT"),
    ans("इनकम टैक्स रिफंड आने वाला है, उसके लिए प्रोसेसिंग फीस भरनी है", SCAM,
        Q2=("yes", "हाँ, टैक्स ऑफिस से फोन आया"),
        Q4=("yes", "हाँ, इनकम टैक्स विभाग"),
        Q7=("yes", "हाँ, रिफंड के साथ फीस भी वापस मिलेगी"))))

# --- genuine (16: 8 dev, 8 test; hard negatives marked) ---------------------------------------------
S.append(sc("gen_01", "Daughter's wedding, venue and caterer (demo 3)", "dev", "hi", "genuine",
    txn(62, 60000, 200000, 1200000, "RTGS"),
    ans("बेटी की शादी है, वेन्यू और कैटरर को एडवांस देना है", GENUINE,
        Q3=("yes", "हाँ, मैरिज हॉल वाले को जानते हैं"),
        Q10=("yes", "हाँ, बेटा बाहर ही खड़ा है"))))

S.append(sc("gen_02", "Flat balance payment to builder", "dev", "en", "genuine",
    txn(55, 120000, 500000, 3500000, "RTGS"),
    ans("Balance payment for a flat; registration is next week at the sub-registrar office.", GENUINE,
        Q2=("yes", "The builder's office sent the payment schedule"),
        Q3=("yes", "Yes, I have met the builder and signed the agreement"))))

S.append(sc("gen_03", "Wife's operation, hospital bill", "dev", "hinglish", "genuine",
    txn(66, 40000, 150000, 450000, "NEFT"),
    ans("Wife ka operation hai, hospital ka bill bharna hai", GENUINE,
        Q3=("yes", "haan, hospital ka hi account hai, bill saath laaya hoon"))))

S.append(sc("gen_04", "Hard negative: passport police verification, visa and tickets", "dev", "en", "genuine",
    txn(34, 50000, 100000, 240000, "NEFT"),
    ans("Police verification for my passport is done; paying the travel agent for my Canada visa and tickets.",
        GENUINE,
        Q4=("yes", "Only the local police came for my passport verification last week"))))

S.append(sc("gen_05", "Hard negative: land case, lawyer's fees for High Court", "dev", "hi", "genuine",
    txn(68, 30000, 100000, 300000, "RTGS"),
    ans("ज़मीन के केस के लिए वकील की फीस है, हाई कोर्ट में सुनवाई है", GENUINE,
        Q3=("yes", "हाँ, हमारे पुराने वकील हैं"),
        Q4=("yes", "हाँ, कोर्ट से नोटिस आया था, पर वो हमारे केस का है"))))

S.append(sc("gen_06", "Hard negative: son's university fees abroad, son on video call", "dev", "hinglish",
    "genuine",
    txn(57, 100000, 300000, 1400000, "OTHER", new=False, call=True),
    ans("Bete ki Toronto university ki semester fees", GENUINE,
        Q2=("yes", "bete ne invoice bheja hai email pe"),
        Q3=("yes", "university hai, pichle semester bhi bhara tha"),
        Q6=("yes", "beta video call par hai, fees confirm kar raha hai"),
        Q10=("yes", "haan, beta video call pe hai, baat kar lo"))))

S.append(sc("gen_07", "Hard negative: senior on call with son, paying new contractor", "dev", "en", "genuine",
    txn(73, 35000, 150000, 800000, "RTGS", call=True),
    ans("Paying the contractor for repairs to our house; my son is on the phone guiding me.", GENUINE,
        Q2=("yes", "My son asked me to pay the contractor"),
        Q3=("no", "I have not met him, my son hired him"),
        Q6=("yes", "My son, he lives in Pune"),
        Q10=("yes", "Yes, my son is on the line, please talk to him"))))

S.append(sc("gen_08", "FD moved to own account in another bank", "dev", "hi", "genuine",
    txn(64, 50000, 200000, 1000000, "FD_BREAK"),
    ans("एफडी तोड़कर अपने दूसरे बैंक खाते में डाल रहा हूँ, वहाँ ब्याज ज़्यादा है", GENUINE,
        Q3=("yes", "मेरा ही खाता है"))))

S.append(sc("gen_09", "New car from dealership", "test", "en", "genuine",
    txn(41, 150000, 300000, 900000, "RTGS"),
    ans("Buying a new car; paying the dealership, I have the invoice.", GENUINE,
        Q3=("yes", "Yes, it's the dealer's account on the invoice"))))

S.append(sc("gen_10", "Monthly supplier payment", "test", "hinglish", "genuine",
    txn(49, 400000, 900000, 700000, "RTGS", new=False),
    ans("Kapde ke supplier ka payment, har mahine karte hain", GENUINE,
        Q2=("yes", "supplier ne bill bheja"))))

S.append(sc("gen_11", "Children's annual school fees", "test", "hi", "genuine",
    txn(39, 60000, 120000, 160000, "NEFT"),
    ans("बच्चों की स्कूल की सालाना फीस", GENUINE,
        Q3=("yes", "स्कूल का ही खाता है, रसीद मिलेगी"))))

S.append(sc("gen_12", "Senior buying wedding jewellery from family jeweller", "test", "en", "genuine",
    txn(70, 50000, 200000, 600000, "RTGS"),
    ans("Buying gold jewellery for my granddaughter's wedding from our family jeweller.", GENUINE)))

S.append(sc("gen_13", "Hard negative: on call with daughter, paying her society dues", "test", "hinglish",
    "genuine",
    txn(69, 30000, 100000, 300000, "NEFT", call=True),
    ans("Meri beti phone par hai, uske flat ka maintenance aur property tax bhar raha hoon", GENUINE,
        Q2=("yes", "beti ne bola"),
        Q3=("no", "society ka account hai, beti ne bheja"),
        Q6=("yes", "beti hai, Bangalore se"),
        Q10=("yes", "haan, beti line par hi hai"))))

S.append(sc("gen_14", "Hard negative: courier company's own bill (Q4 yes)", "test", "hi", "genuine",
    txn(52, 80000, 150000, 200000, "NEFT", new=False),
    ans("हमारी दुकान का कूरियर कंपनी का तीन महीने का बिल", GENUINE,
        Q2=("yes", "कंपनी ने बिल भेजा है"),
        Q4=("yes", "हाँ, कूरियर कंपनी का ही बिल है"))))

S.append(sc("gen_15", "Hard negative: stamp duty into the government account", "test", "en", "genuine",
    txn(60, 50000, 150000, 400000, "NEFT"),
    ans("Stamp duty for my new flat, paid into the government account through the e-challan.", GENUINE)))

S.append(sc("gen_16", "Home repairs, known contractor, son-in-law present", "test", "hinglish", "genuine",
    txn(66, 45000, 150000, 500000, "RTGS", notes="Son-in-law accompanying, customer introduced him"),
    ans("Ghar ki marammat, thekedaar ko payment, damaad saath aaye hain", GENUINE,
        Q3=("yes", "haan, purane thekedaar hain"))))


def main() -> int:
    ids = [s["id"] for s in S]
    assert len(S) == 40 and len(set(ids)) == 40, "need 40 unique scenarios"
    assert sum(s["split"] == "dev" for s in S) == 20
    assert sum(s["label"]["is_scam"] for s in S) == 24
    assert sum(s["label"]["coached"] for s in S) >= 5
    OUT.mkdir(parents=True, exist_ok=True)
    for s in S:
        (OUT / f"{s['id']}.json").write_text(json.dumps(s, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(S)} scenarios to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
