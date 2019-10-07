$(document).ready(function () {
  const body = $('body');

  body.on('click', '[data-update-select]', function (event) {
    const el = $(event.target);
    const selectInput = el.parents('.dropdown-select-submit').find('select');
    const value = el.attr('data-update-select');

    // Update bound <select> value:
    selectInput.val(value);

    const form = el.parents('form');
    sendControlForm(form);
  });

  const sendControlForm = function (form) {
    const formData = form.serialize();
    const parentFeedItem = form.parents('[data-html-src]');
    $.ajax({
      url: form.attr('action'),
      method: form.attr('method'),
      data: formData,
    }).done(function () {
      if (form.hasClass('inst-form-delete')) {
        parentFeedItem.remove();
      } else if (parentFeedItem.length > 0) {
        const url = parentFeedItem.attr('data-html-src');
        $.get(url, function (data) {
          parentFeedItem.html(data);
        });
      } else {
        window.location.reload();
      }
    });
    parentFeedItem.html(
      '<div class="d-flex"><div class="mx-auto text-center"><div class="spinner-border"></div><p>Loading</p></div></div>'
    )
  };
});
