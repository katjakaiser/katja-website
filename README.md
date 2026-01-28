# 🌟 Katja Kaiser - Website & Landingpages

Website und Landingpages für **Katja Kaiser Coaching** - Executive Performance, Selbstführung & Breathwork

---

## 📂 Struktur

```
katja-website/
├── performance-check/          # Executive Performance Check 2026 Landingpage
│   └── index.html
├── images/                     # Bilder für alle Seiten
│   └── (deine Fotos hier)
└── README.md                   # Diese Datei
```

---

## 🚀 Live-Seiten

- **Performance Check Landingpage:** `https://katjakaiser-coaching.de/performance-check/`

---

## 🎨 Features der Performance Check Landingpage

### Premium-Design
- ✨ Luxuriöses Gold-Farbschema
- 💎 Glassmorphism-Effekte
- 🎭 Smooth Scroll-Animationen
- 📱 Vollständig responsive (Mobile, Tablet, Desktop)

### Technologie
- Pure HTML5 + CSS3
- Vanilla JavaScript
- Google Fonts (Cormorant Garamond + Inter)
- Optimierte Performance

### Sections
1. **Hero** - Kraftvolle Headline mit Foto
2. **Trust Bar** - Vertrauenssignale
3. **Problem** - Pain Points der Zielgruppe
4. **Features** - 6 Bereiche des Checks
5. **Formular** - Active Campaign Integration
6. **Testimonial** - Social Proof
7. **CTA** - Final Call-to-Action
8. **Footer** - Links & Copyright

---

## 📝 Anpassungen vornehmen

### 1. Dein Foto einsetzen

**Schritt 1:** Foto vorbereiten
- Format: Quadratisch (800x800px oder größer)
- Dateiformat: JPG oder PNG
- Dateiname: z.B. `katja-kaiser-portrait.jpg`

**Schritt 2:** Foto hochladen
- Foto in den Ordner `/images/` legen

**Schritt 3:** In HTML einbinden
- Öffne: `performance-check/index.html`
- Suche nach Zeile 709 (ca.):
```html
<img src="https://images.unsplash.com/photo-1580489944761-15a19d654956?w=800&q=80" ...>
```
- Ersetze mit:
```html
<img src="/images/katja-kaiser-portrait.jpg" ...>
```

### 2. Active Campaign Formular einbinden

**Schritt 1:** In Active Campaign
- Gehe zu "Forms"
- Erstelle ein neues Formular (Inline)
- Kopiere den Embed-Code

**Schritt 2:** In HTML einfügen
- Öffne: `performance-check/index.html`
- Suche nach: `<!-- HIER KOMMT DEIN ACTIVE CAMPAIGN FORMULAR HIN -->`
- Ersetze den Platzhalter-Bereich mit deinem Code

### 3. Links anpassen

In der Datei `performance-check/index.html` (ca. Zeile 878-883):

```html
<a href="https://www.katjakaiser-coaching.de">Website</a>
<a href="https://www.katjakaiser-coaching.de/impressum">Impressum</a>
<a href="https://www.katjakaiser-coaching.de/datenschutz">Datenschutz</a>
<a href="mailto:impressum@katjakaiser-coaching.de">Kontakt</a>
```

Passe die URLs an deine echten Seiten an!

---

## 🔧 Auf Server hochladen

### Option 1: Manuell per FTP (FileZilla)

1. **FileZilla öffnen**
2. **Mit Server verbinden:**
   - Host: `ftp.katjakaiser-coaching.de`
   - Benutzername: [dein FTP-User]
   - Passwort: [dein FTP-Passwort]
   - Port: 21

3. **Ordner erstellen:**
   - Navigiere zu `/public_html/`
   - Erstelle Ordner: `performance-check`

4. **Dateien hochladen:**
   - Lokaler Ordner: `performance-check/`
   - Remote-Ordner: `/public_html/performance-check/`
   - Alle Dateien hochladen

5. **Images hochladen:**
   - Lokaler Ordner: `images/`
   - Remote-Ordner: `/public_html/images/`

### Option 2: GitHub Actions (Auto-Deploy)

**Wird noch eingerichtet!** 🚀

---

## 📋 Nächste Schritte

- [ ] Dein Foto einsetzen
- [ ] Active Campaign Formular einbinden
- [ ] Links anpassen (Impressum, Datenschutz)
- [ ] Per FTP auf Server hochladen
- [ ] Testen: https://katjakaiser-coaching.de/performance-check/
- [ ] Formular-Test durchführen

---

## 🆘 Hilfe & Support

Bei Fragen oder Problemen:
1. Prüfe diese README-Datei
2. Schaue in die Upload-Checkliste
3. Kontaktiere deinen Entwickler

---

## 📜 Lizenz & Copyright

© 2026 Katja Kaiser - Alle Rechte vorbehalten

---

**Erstellt mit ❤️ für professionelles Executive Coaching**