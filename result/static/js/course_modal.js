$(function () {

  $(".js-course-book").click(function () {
    $.ajax({
      url: '/courses/add/new',
      type: 'get',
      dataType: 'json',
      beforeSend: function () {
        $("#modalLoginForm").modal("show");
      },
      success: function (data) {
        $("#modalLoginForm .modal-content").html(data.html_form);
      }
    });
  });

});
