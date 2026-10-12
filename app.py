<script>
  setInterval(function() {
    fetch('/api/sensex-live')
      .then(response => response.json())
      .then(data => {
        const valElem = document.querySelector('.sensex-value, #sensex-value');
        const changeElem = document.querySelector('.sensex-change, #sensex-change');
        const timeElem = document.querySelector('.sensex-time, #sensex-time');

        if (valElem) valElem.innerText = data.value;
        if (changeElem) {
          changeElem.innerText = data.change;
          changeElem.className = data.is_positive ? 'text-success' : 'text-danger';
        }
        if (timeElem) timeElem.innerText = data.time_label;
      })
      .catch(err => console.error('Live sync error:', err));
  }, 10000); // Refreshes every 10 seconds automatically
</script>
