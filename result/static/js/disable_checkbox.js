$(document).ready(function() {
	var defaultUnit = $("#units").html()
	$('input[type="checkbox"]').change(function(){
		var units = parseInt(defaultUnit);
			$.each($("input[type='checkbox']:checked"), function(){  
				units = units + parseInt(($(this).val()));
                if(units > 24){
                    $("#add_selected").prop('disabled', true);
                    $("label").style('background-color', 'red');
                                    
                }else{
                    $("#add_selected").prop('disabled', false);    
                }
		});
			$("#units").html(units);
	});
	///////////
});
