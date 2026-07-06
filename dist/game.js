// Vice Heist Frontend - Connects to Stake math
let balance = 1000.00;
const bet = 1.0;

document.getElementById('spin').addEventListener('click', () => {
    if (balance < bet) return alert("Insufficient balance!");
    balance -= bet;
    updateUI();
    
    // Simulate spin (replace with full math integration / API call)
    fetch('/api/spin', { method: 'POST', body: JSON.stringify({bet}) })
        .then(r => r.json())
        .then(result => {
            document.getElementById('log').innerHTML = `Spin Result: ${JSON.stringify(result.reel_grid)} Win: ${result.win}`;
            balance += result.win || 0;
            updateUI();
        });
});

document.getElementById('bonus-buy').addEventListener('click', () => {
    alert("Bonus Buy triggered (100x) - Implement full feature");
});

function updateUI() {
    document.getElementById('balance').textContent = balance.toFixed(2);
}

// Initial load
updateUI();
