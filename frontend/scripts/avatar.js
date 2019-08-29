(function ($) {
  //////////////////////////////
  // TODO: update documentation (we don't submit form anymore, rather do location.reload and add load status
  // Avatar plugin
  //
  // To make things work, a <form> element which action is set to GET (e.g. the page where it is put),
  // must have a class `.dccn-avatar-update-form` and have an attribute `data-target`, which stores a
  // URL for avatar update.
  //
  // The form must also have an <input type="file"> element.
  //
  // Example:
  //
  // <form class="dccn-avatar-update-form" action="/profile" method="GET" data-target="/avatar/update">
  //   <input type="file" value="Choose file...">
  // </form>
  //
  $.fn.dccnAvatarUpdateForm = function () {
    var form = this;  // `this` will point an `<input>` element below
    form.find('input[type="file"]').change(function (event) {
      // `this` is an <input type="file"> (not a jQuery object, plain DOM!)
      var input = this;
      if (input.files && input.files[0]) {
        var sizeKb = (input.files[0].size / 1024).toFixed(4);
        if (sizeKb > 1000) {
          Swal.fire({
            type: 'warning',
            text: `Profile image size must be under 1000KB, your file is ${sizeKb}KB`,
            customClass: {
              confirmButton: 'btn btn-outline-secondary mx-2',
            },
            buttonsStyling: false
          });
        } else {
          var data = new FormData(form.get(0));
          var reader = new FileReader();
          reader.onload = function (re) {
            Swal.fire({
              text: 'Use this as your profile picture?',
              imageUrl: re.target.result,
              imageWidth: 240,
              imageHeight: 240,
              imageAlt: 'new profile picture',
              animation: false,
              showCancelButton: true,
              cancelButtonText: 'No',
              confirmButtonText: 'Yes',
              customClass: {
                image: 'img-fluid rounded-circle',
                confirmButton: 'btn btn-success mx-2',
                cancelButton: 'btn btn-outline-secondary mx-2',
              },
              buttonsStyling: false
            }).then(result => {
              if (result.value) {
                var req = new XMLHttpRequest();
                req.open("POST", form.attr('data-target'), true);
                req.onload = function (xe) {
                  location.reload();
                };
                data.append('avatar', re.target.result);
                data.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]').val());
                req.send(data);

                // Display progress
                var preview = $(form.attr('data-preview'));
                preview.html(
                  '<div style="width: 120px; height: 120px; padding: 30px; margin: 0;">' +
                  '<div class="spinner-border dccn-loading-progress" ' +
                       'style="margin: 0; padding: 0; width: 60px; height: 60px;" role="status">' +
                  '<span class="sr-only">Loading...</span>' +
                  '</div></div>'
                )
              } else {
                $(input).val('');
              }
            });
          };
          reader.readAsDataURL(input.files[0]);
        }
      }
      event.preventDefault();
    });
  };

  //////////////////////////////
  // Associating the plugins
  $('.dccn-avatar-update-form').dccnAvatarUpdateForm();
}(jQuery));

