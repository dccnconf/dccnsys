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

  body.on('submit', 'form.decision-control-form', event => {
    const form = $(event.target);
    const container = form.parent();
    const formData = form.serialize();
    $.ajax({
      url: form.attr('action'),
      method: form.attr('method'),
      data: formData,
    }).done(data => {
      container.html(data);
    });
    event.stopPropagation();
    return false;
  });
});