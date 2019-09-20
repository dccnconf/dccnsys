$(document).ready(function () {
  const body = $('body');

  const updateUser = function (el, target, csrf, data={}) {
    const formData = Object.assign({}, data);
    formData[csrf.attr('name')] = csrf.val();
    $.post(target, formData, function () {
      const reloadableParent = el.parents('[data-html-src]');
      if (reloadableParent.length > 0) {
        const htmlURL = reloadableParent.attr('data-html-src');
        $.get(htmlURL, function (html) {
          reloadableParent.html(html);
        });
      } else {
        window.location.reload(true);
      }
    });
  };

  /*
   * For all buttons with 'data-toggle="submission-status"' we show a bootbox modal dialog,
   * in which we send AJAX POST for status update.
   *
   * !!! This button MUST contain {% csrf_token %} inside !!!
   */
  body.on('click', 'button[data-toggle="user-update"]', function () {
    const btn = $(this);
    const action = btn.attr('data-user-action');
    const target = btn.attr('data-target');
    const csrf = btn.find('input[type="hidden"]');
    const name = btn.attr('data-user-name');

    const message = {
      'make-reviewer': `${name} will become a reviewer`,
      'revoke-reviewer': `${name} won't be a reviewer anymore.<br>Any reviews he or she wrote will be lost`,
    }[action];

    const dialog = bootbox.confirm({
      message: `<p class="dccn-text-small">${message}.</p>`,
      buttons: {
        cancel: {label: 'Cancel', className: 'btn-sm btn-outline-secondary'},
        confirm: {label: 'Update', className: 'btn-sm btn-outline-primary'}
      },
      centerVertical: true,
      callback: function (result) {
        if (result)
          updateUser(btn, target, csrf);
        dialog.hide();
      }
    });
  });
});
