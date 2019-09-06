$(document).ready(function () {
  const body = $('body');

  /*
   * I. INSTANT FORMS
   *
   * Instant forms are the forms composed of dropdowns with actions, which are submitted
   * immediately after any button is clicked. These forms are expected to be somewhere
   * inside the .dccn-feed-item elements.
   *
   * Submission of instant form causes feed item reloading.
   *
   * Example: decision control form (accept/reject, then proceedings type, then volume).
   */

  // First, we bind click events on any instant form control element to filling
  // the corresponding input fields and form submission:
  body.on('click', '.inst-form-btn[data-form-id][data-value][data-name]',  event => {
    const btn = $(event.target);
    const form = $(btn.attr('data-form-id'));
    const value = btn.attr('data-value');
    const fieldName = btn.attr('data-name');

    // The form which is submitted to the server is expected to have a hidden input
    // with the name given in 'data-name' button attribute. Its value is filled
    // from 'data-value' attribute and submitted to the server:
    form.find(`input[name=${fieldName}]`).val(value);
    form.submit();
  });

  // Secondly, we define a function which is called upon form submission. In this
  // function the form serialized and send, and upon receiving response, a card
  // is re-leaded:
  const sendControlForm = function (form) {
    const formData = form.serialize();
    const parentFeedItem = form.parents('.dccn-feed-item');
    $.ajax({
      url: form.attr('action'),
      method: form.attr('method'),
      data: formData,
    }).done(function () {
      const url = parentFeedItem.attr('data-html-src');
      $.get(url, function (data) {
        parentFeedItem.html(data);
      });
    });
  };

  // Thirdly, we bind `sendControlForm` handler to form submission. Here we
  // also check whether the form is contained in a modal dialog (which is defined
  // inside the feed item). If the form is inside the modal dialog, we first
  // need to hide it before actual form submission.
  body.on('submit', 'form.inst-form', event => {
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