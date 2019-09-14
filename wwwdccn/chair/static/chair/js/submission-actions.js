$(document).ready(function () {
  /*
   * For all buttons with 'data-toggle="submission-status"' we show a bootbox modal dialog,
   * in which we send AJAX POST for status update.
   *
   * !!! This button MUST contain {% csrf_token %} inside !!!
   */
  $('body').on('click', 'button[data-toggle="submission-status"]', function () {
    console.log('click!');
    const btn = $(this);
    const target = btn.attr('data-target');
    const status = btn.attr('data-status');
    const csrf = btn.find('input[type="hidden"]');

    const dialog = bootbox.confirm({
      message:
        `<p class="dccn-text-small">Submission status will be changed to <span class="font-weight-bold">${status}</span>.`,
      buttons: {
        cancel: {label: 'Cancel', className: 'btn-sm btn-outline-secondary'},
        confirm: {label: 'Update', className: 'btn-sm btn-outline-primary'}
      },
      centerVertical: true,
      callback: function (result) {
        // If use pressed OK, we send the request and refresh the surrounding content:
        if (result) {
          const formData = {status: status};
          formData[csrf.attr('name')] = csrf.val();
          $.post(target, formData, function () {
            const reloadableParent = btn.parents('[data-html-src]');
            if (reloadableParent.length > 0) {
              const htmlURL = reloadableParent.attr('data-html-src');
              $.get(htmlURL, function (html) {
                reloadableParent.html(html);
              });
            }
          });
        }
        dialog.hide();
      }
    });
  });
});