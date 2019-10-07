$(document).ready(function () {
  const body = $('body');

  const handleDialogResult = function (el, result, target, params) {
    // If use pressed OK, we send the request and refresh the surrounding content:
    if (result) {
      const csrf = el.find('input[type="hidden"]');
      const formData = $.extend({}, params);
      formData[csrf.attr('name')] = csrf.val();
      const reloadableParent = el.parents('[data-html-src]');
      if (reloadableParent.length > 0) {
        reloadableParent.html('<div class="d-flex"><div class="mx-auto text-center"><div class="spinner-border"></div><p>Loading</p></div></div>');
      }
      $.post(target, formData, function () {
        if (reloadableParent.length > 0) {
          const htmlURL = reloadableParent.attr('data-html-src');
          $.get(htmlURL, function (html) {
            reloadableParent.html(html);
          });
        } else {
          window.location.reload();
        }
      });
    }
  };

  /*
   * For all buttons with 'data-toggle="submission-status"' we show a bootbox modal dialog,
   * in which we send AJAX POST for status update.
   *
   * !!! This button MUST contain {% csrf_token %} inside !!!
   */
  body.on('click', 'button[data-toggle="submission-status"]', function () {
    const btn = $(this);
    const target = btn.attr('data-target');
    const status = btn.attr('data-status');

    const dialog = bootbox.confirm({
      message:
        `<p class="dccn-text-small">Submission status will be changed to <span class="font-weight-bold">${status}</span>.`,
      buttons: {
        cancel: {label: 'Cancel', className: 'btn-sm btn-outline-secondary'},
        confirm: {label: 'Update', className: 'btn-sm btn-outline-primary'}
      },
      centerVertical: true,
      callback: function (result) {
        handleDialogResult(btn, result, target, {status: status});
        dialog.hide();
      }
    });
  });


  /*
   * For all buttons with 'data-toggle="submission-review-decision"' we show a bootbox modal dialog,
   * in which we send AJAX POST for status update.
   *
   * !!! This button MUST contain {% csrf_token %} inside !!!
   */
  body.on('click', 'button[data-toggle="submission-review-decision"]', function () {
    const btn = $(this);
    const target = btn.attr('data-target');
    const reviewDecision = btn.attr('data-review-decision');
    const rejectOrAccept = btn.attr('data-decision-value');
    const decisionTypeId = btn.attr('data-decision-type-id');

    const iconClass = rejectOrAccept === 'reject' ? 'fa-thumbs-down text-danger' : 'fa-thumbs-up text-success';
    const submissionActionString = rejectOrAccept === 'reject'
      ? `<span class="text-danger font-weight-bold">rejected</span>`
      : `<span class="text-success font-weight-bold">accepted</span>`

    const message = `
<div class="d-flex align-items-center">
  <div class="mr-3"><i class="fa-2x far ${iconClass}"></i></div>
  <div class="dccn-text-normal">
    Decision will be set to "<span class="font-weight-bold">${reviewDecision}</span>", submission will be ${submissionActionString}.
  </div>
</div>`;

    const dialog = bootbox.confirm({
      message: message,
      buttons: {
        cancel: {label: 'Cancel', className: 'btn-sm btn-outline-secondary'},
        confirm: {label: 'Update', className: 'btn-sm btn-outline-primary'}
      },
      centerVertical: true,
      callback: function (result) {
        handleDialogResult(btn, result, target, {decision_type: decisionTypeId});
        dialog.hide();
      }
    });
  });

});