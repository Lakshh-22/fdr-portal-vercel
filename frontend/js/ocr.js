// OCR: reads an FDR scan/photo/PDF in the browser (Tesseract.js; PDFs via pdf.js) and extracts the form fields.
const BANKMAP = [['State Bank of India|\\bSBI\\b', 'SBI'], ['Canara', 'Canara Bank'], ['Indian Bank', 'Indian Bank'], ['HDFC', 'HDFC Bank'], ['Bank of Baroda|\\bBOB\\b', 'Bank of Baroda'], ['Punjab National|\\bPNB\\b', 'Punjab National Bank'], ['Union Bank', 'Union Bank']];
const MON = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12 };
const DATE_RE = '(\\d{4}[-/.]\\d{1,2}[-/.]\\d{1,2}|\\d{1,2}[-/. ]\\d{1,2}[-/. ]\\d{2,4}|\\d{1,2}[-/. ]?[A-Za-z]{3,9}[-/. ,]*\\d{2,4})';
function isoDate(s) {
  s = s.trim(); let m, d, mo, y;
  if (m = s.match(/^(\d{4})[-\/.](\d{1,2})[-\/.](\d{1,2})$/)) { y = +m[1]; mo = +m[2]; d = +m[3]; }
  else if (m = s.match(/^(\d{1,2})[-\/. ](\d{1,2})[-\/. ](\d{2,4})$/)) { d = +m[1]; mo = +m[2]; y = +m[3]; if (y < 100) y += 2000; }
  else if (m = s.match(/^(\d{1,2})[-\/. ]?([A-Za-z]{3})[a-z]*[-\/. ,]*(\d{2,4})$/)) { d = +m[1]; mo = MON[m[2].toLowerCase()]; y = +m[3]; if (y < 100) y += 2000; }
  if (!d || !mo || mo > 12 || d > 31 || y < 2000 || y > 2100) return null;
  return `${y}-${String(mo).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
}
// Pure text -> fields (day-first Indian date formats). Returns only what it could find.
function parseFdrText(text) {
  const o = {}, T = text.replace(/[|]/g, ' ').replace(/\r/g, '');
  for (const [re, b] of BANKMAP) if (new RegExp(re, 'i').test(T)) { o.bank = b; break; }
  let m = T.match(/(?:FDR|F\.D\.R|Deposit|Receipt|Account|A\/c)\s*(?:No\.?|Number|Num|#)\s*[:.\-]?\s*([A-Z]{0,5}[\s\-]?\d[A-Z0-9\/\-]{4,})/i);
  if (m) o.number = m[1].replace(/\s+/g, '').toUpperCase();
  m = T.match(/(?:Principal|Deposit\s*Amount|Amount\s*(?:of\s*Deposit)?|Sum)\D{0,25}?([\d,]{5,}(?:\.\d{1,2})?)/i) || T.match(/(?:Rs\.?|INR|₹)\s*([\d,]{5,}(?:\.\d{1,2})?)/i);
  if (m) { const a = parseFloat(m[1].replace(/,/g, '')); if (a > 0) o.amount = a; }
  const lab = re => { const x = T.match(new RegExp('(?:' + re + ')[^\\d\\n]{0,20}?' + DATE_RE, 'i')); return x ? isoDate(x[1]) : null; };
  o.maturity = lab('Maturity\\s*Date|Date\\s*of\\s*Maturity|Due\\s*Date|Matures?\\s*on');
  o.issue = lab('Issue\\s*Date|Date\\s*of\\s*(?:Deposit|Issue)|Deposit\\s*Date|Value\\s*Date|Start\\s*Date|Opening\\s*Date');
  if (!o.issue || !o.maturity) {
    const ds = [...T.matchAll(new RegExp(DATE_RE, 'g'))].map(x => isoDate(x[1])).filter(Boolean).sort();
    if (ds.length > 1) { o.issue = o.issue || ds[0]; o.maturity = o.maturity || ds[ds.length - 1]; }
  }
  Object.keys(o).forEach(k => o[k] == null && delete o[k]); return o;
}
const loadJs = u => new Promise((res, rej) => { if (document.querySelector(`script[src="${u}"]`)) return res(); const s = document.createElement('script'); s.src = u; s.onload = res; s.onerror = () => rej(new Error('Could not load ' + u + ' (internet needed for OCR)')); document.head.appendChild(s); });
async function ocrImg(img, say) {
  say('Reading text from the image (first time it downloads the OCR engine)…');
  await loadJs('https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js');
  const r = await Tesseract.recognize(img, 'eng', { logger: m => m.status == 'recognizing text' && say('Reading text… ' + Math.round(m.progress * 100) + '%') });
  return r.data.text;
}
async function readDoc(file, say) {
  if (/\.pdf$/i.test(file.name) || file.type == 'application/pdf') {
    say('Reading PDF…'); const base = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/';
    await loadJs(base + 'pdf.min.js'); pdfjsLib.GlobalWorkerOptions.workerSrc = base + 'pdf.worker.min.js';
    const pdf = await pdfjsLib.getDocument({ data: await file.arrayBuffer() }).promise, pg = await pdf.getPage(1);
    const tx = (await pg.getTextContent()).items.map(i => i.str).join('\n'); if (tx.replace(/\s/g, '').length > 40) return tx;   // digital PDF: exact text
    const vp = pg.getViewport({ scale: 2.2 }), cv = document.createElement('canvas'); cv.width = vp.width; cv.height = vp.height;
    await pg.render({ canvasContext: cv.getContext('2d'), viewport: vp }).promise;                                          // scanned PDF: OCR the page image
    return ocrImg(await new Promise(r => cv.toBlob(r, 'image/png')), say);
  }
  return ocrImg(file, say);
}
async function ocrFill(file) {
  const msg = $('#msg'), say = t => { msg.className = 'sm'; msg.textContent = t; }; let o = {}, src = 'the document', why = '';
  try { o = parseFdrText(await readDoc(file, say)); } catch (e) { console.error(e); why = e.message || String(e); say('OCR not available: ' + why); }
  if (!Object.keys(o).length) {   // fallback: file name like FDR_SBI_778299_500000.pdf
    const m = file.name.replace(/\.\w+$/, '').split('_'), b = BANKS.find(x => m[1] && x.toUpperCase().startsWith(m[1].toUpperCase().slice(0, 3)));
    if (b && m[2]) { o = { bank: b, number: m[1].toUpperCase() + m[2] }; if (m[3]) o.amount = +m[3]; src = 'the file name'; }
  }
  if (o.bank) $('#nb').value = o.bank; if (o.number) $('#nn').value = o.number; if (o.amount) $('#na').value = o.amount; if (o.issue) $('#ni').value = o.issue; if (o.maturity) $('#nm').value = o.maturity;
  const n = Object.keys(o).length; msg.className = (n ? 'ok' : 'er') + ' sm';
  msg.textContent = n ? `Read from ${src}: ${Object.keys(o).join(', ')}. Please check the values before submitting.` : 'Could not read details from this file' + (why ? ' (' + why + ')' : '') + '. Please enter them manually.';
}
