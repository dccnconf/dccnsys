$(document).ready(function () {
  const body = $('body');
  body.on('click', 'button[data-form-id][data-value][data-name]',  event => {
    const btn = $(event.target);
    const form = $(btn.attr('data-form-id'));
    const value = btn.attr('data-value');
    const fieldName = btn.attr('data-name');
    form.find(`input[name=${fieldName}]`).val(value);
    form.submit();
  });

  const sendControlForm = function (form) {
    const formData = form.serialize();
    $.ajax({
      url: form.attr('action'),
      method: form.attr('method'),
      data: formData,
    }).done(data => {
      form.parents('.dccn-feed-item').html(data);
    });
  };

  body.on('submit', 'form.decision-control-form', event => {
    const form = $(event.target);
    const modalParent = form.parents('.modal');
    if (modalParent.length > 0) {
      modalParent.on('hidden.bs.modal', function () {
        sendControlForm(form);
      });
      modalParent.modal('hide');
    } else {
      sendControlForm(form);
    }
    event.stopPropagation();
    return false;
  });
});