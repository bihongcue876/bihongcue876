/* 探针：验证 README（github.com 的 md 渲染页）里的 <script> 到底会不会执行。
 *
 * 用法：README 里写  <script src="./docs/heatmap/live.js"></script>
 *
 * 如果脚本真的跑起来了，你会看到：
 *   1. 页面上多出一条绿色徽章「✅ live.js 已执行 · 时间」；
 *   2. 下面 12 张月度小图变成可点——点一下就把上面的大图换成那个月，
 *      再点「回到全年」。←/→ 键也能切月。
 * 如果什么都没出现，说明 github.com 把 <script> 剥掉了（大概率就是这个结果）。
 */
(function () {
  window.__HM_TEST__ = { ran: true, at: new Date().toISOString(), version: 1 };

  function cx(css, tag) {
    var el = document.createElement(tag || 'div');
    el.style.cssText = css;
    return el;
  }

  function boot() {
    var root = document.querySelector('.markdown-body') || document.body;
    if (!root) return;
    if (document.getElementById('hm-live-badge')) return;

    /* ---- 1. 明显的"我在跑" ---- */
    var badge = cx('display:inline-block;margin:10px 0;padding:6px 12px;border-radius:8px;' +
      'background:#1f883d;color:#fff;font:600 13px/1.4 -apple-system,BlinkMacSystemFont,sans-serif;' +
      'box-shadow:0 2px 8px rgba(31,136,61,.35)');
    badge.id = 'hm-live-badge';
    badge.textContent = '✅ live.js 已执行 · ' + new Date().toLocaleString();
    root.insertBefore(badge, root.firstChild);

    /* ---- 2. 月度小图变成「点一下换大图」 ---- */
    var big = null;
    [].slice.call(root.querySelectorAll('img')).some(function (img) {
      if (/heatmap-(light|dark)\.svg$/.test(img.getAttribute('src') || '')) { big = img; return true; }
      if (/years\/year-\d{4}-(light|dark)\.svg$/.test(img.getAttribute('src') || '')) { big = big || img; }
      return false;
    });
    if (!big) return;
    var original = big.getAttribute('src');
    var cards = [].slice.call(root.querySelectorAll('img[src*="months/"]'));
    if (!cards.length) return;

    var caption = cx('margin-top:6px;font:400 12px/1.5 -apple-system,sans-serif;color:#57606a');
    caption.id = 'hm-live-caption';
    big.parentNode.insertBefore(caption, big.nextSibling);

    function select(i) {
      var card = cards[(i + cards.length) % cards.length];
      var src = card.getAttribute('src').replace(/^\.\//, '');
      if (big.getAttribute('src') === src) {           // 再点一次 = 回到全年
        big.setAttribute('src', original);
        caption.textContent = '';
        return;
      }
      big.setAttribute('src', src);
      var title = card.getAttribute('title') || card.getAttribute('alt') || '';
      caption.textContent = '← 正在看：' + title + '（再点一次回到全年，←/→ 换月）';
    }

    cards.forEach(function (card, i) {
      card.style.cursor = 'zoom-in';
      card.style.transition = 'transform .15s ease';
      card.addEventListener('click', function (e) { e.preventDefault(); select(i); });
      card.addEventListener('mouseenter', function () { card.style.transform = 'translateY(-2px)'; });
      card.addEventListener('mouseleave', function () { card.style.transform = ''; });
    });

    var cur = 0;
    document.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { cur = (cur + 1) % cards.length; select(cur); }
      if (e.key === 'ArrowLeft') { cur = (cur - 1 + cards.length) % cards.length; select(cur); }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
