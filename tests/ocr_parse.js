// Tests the OCR text -> fields parser. Usage: node tests/ocr_parse.js [file-with-ocr-text ...]
const fs = require('fs'), vm = require('vm'), path = require('path'); const ctx = {}; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'frontend', 'js', 'ocr.js'), 'utf8'), ctx);
const eq = (n, got, want) => { const ok = JSON.stringify(got) == JSON.stringify(want); console.log(ok ? 'PASS' : 'FAIL', n, ok ? '' : '\n  got ' + JSON.stringify(got) + '\n  want ' + JSON.stringify(want)); if (!ok) process.exitCode = 1; };
eq('labelled receipt', ctx.parseFdrText('Bank: Indian Bank\nFDR No: IB550123\nDeposit Amount: Rs. 5,00,000.00\nDate of Deposit: 12/03/2026\nMaturity Date: 12/03/2027'), { bank: 'Indian Bank', number: 'IB550123', amount: 500000, maturity: '2027-03-12', issue: '2026-03-12' });
eq('month names', ctx.parseFdrText('STATE BANK OF INDIA\nReceipt No. SBI778299\nPrincipal Amount : INR 7,50,000\nValue Date : 05 Jan 2026\nDue Date : 05 Jan 2028'), { bank: 'SBI', number: 'SBI778299', amount: 750000, maturity: '2028-01-05', issue: '2026-01-05' });
eq('iso dates', ctx.parseFdrText('Canara Bank\nFDR Number: CB210877\nAmount Rs 10,00,000/-\nStart Date: 2026-02-10\nDate of Maturity: 2027-02-10'), { bank: 'Canara Bank', number: 'CB210877', amount: 1000000, maturity: '2027-02-10', issue: '2026-02-10' });
eq('unlabelled dates fall back to earliest/latest', ctx.parseFdrText('HDFC Bank\nFDR No HD330918\n01/04/2026 to 01/04/2027\nRs. 2,50,000'), { bank: 'HDFC Bank', number: 'HD330918', amount: 250000, maturity: '2027-04-01', issue: '2026-04-01' });
eq('garbage gives nothing', ctx.parseFdrText('hello world'), {});
for (const f of process.argv.slice(2)) console.log('\nREAL OCR TEXT', f, '\n  ->', JSON.stringify(ctx.parseFdrText(fs.readFileSync(f, 'utf8'))));
