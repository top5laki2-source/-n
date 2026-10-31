// Cac tuong tac phia client: xac nhan thao tac, loc bang, tu dong tinh Overall.

document.addEventListener('DOMContentLoaded', function () {

  // 1. Xac nhan truoc khi thuc hien thao tac quan trong
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('submit', function (e) {
      if (!window.confirm(el.dataset.confirm)) {
        e.preventDefault();
      }
    });
  });

  // 2. Loc nhanh du lieu trong bang (khong can tai lai trang)
  document.querySelectorAll('[data-filter-target]').forEach(function (input) {
    input.addEventListener('keyup', function () {
      var keyword = input.value.trim().toLowerCase();
      var rows = document.querySelectorAll(input.dataset.filterTarget + ' tbody tr');
      rows.forEach(function (row) {
        row.style.display = row.innerText.toLowerCase().indexOf(keyword) > -1 ? '' : 'none';
      });
    });
  });

  // 3. Tinh band Overall ngay khi giao vien go diem 4 ky nang
  //    Quy tac IELTS: phan le < .25 lam tron xuong, < .75 ve .5, con lai len 1 band
  function ieltsRound(value) {
    var whole = Math.floor(value);
    var frac = value - whole;
    if (frac < 0.25) return whole;
    if (frac < 0.75) return whole + 0.5;
    return whole + 1;
  }

  document.querySelectorAll('tr[data-score-row]').forEach(function (row) {
    var inputs = row.querySelectorAll('input.skill-input');
    var output = row.querySelector('.overall-preview');
    if (!inputs.length || !output) return;

    function recalc() {
      var total = 0;
      var filled = 0;
      inputs.forEach(function (input) {
        var v = parseFloat(input.value);
        if (!isNaN(v)) { total += v; filled++; }
        input.classList.toggle('is-invalid', input.value !== '' && (isNaN(v) || v < 0 || v > 9 || (v * 2) % 1 !== 0));
      });
      if (filled === inputs.length) {
        output.textContent = ieltsRound(total / inputs.length).toFixed(1);
        output.className = 'band-pill overall-preview high';
      } else {
        output.textContent = '—';
        output.className = 'band-pill overall-preview none';
      }
    }

    inputs.forEach(function (input) { input.addEventListener('input', recalc); });
    recalc();
  });

  // 4. Tu dong an thong bao sau 6 giay
  setTimeout(function () {
    document.querySelectorAll('.alert-success, .alert-info').forEach(function (alert) {
      alert.classList.remove('show');
    });
  }, 6000);
});
