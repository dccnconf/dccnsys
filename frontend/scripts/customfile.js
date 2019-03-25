(function ($) {
  $('.dccn-custom-file input.custom-file-input').change(function () {
    var fileName = $(this)[0].files[0].name;
    $(this).next('.custom-file-label').text(fileName);
  });
}(jQuery));
