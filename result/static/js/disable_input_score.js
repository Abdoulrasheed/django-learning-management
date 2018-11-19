function disableTxt() {
    x = document.getElementsByClassName("score");
    for (i = 0; i < x.length; i++){
    	x[i].disabled = true
    }
}

function undisableTxt() {
    x = document.getElementsByClassName("score");
    for (i = 0; i < x.length; i++){
    	x[i].disabled = false
    }
  }
  
function toggle_score_edit() {
	y = document.getElementsByClassName("score");
    check = y[0].disabled
    if (check===false){
        document.getElementById("edit_btn").innerHTML = "Edit"
    	disableTxt();
    }else{
        document.getElementById("edit_btn").innerHTML = "Disable"
    	undisableTxt();
    }
}

x = document.getElementsByClassName("score");
for (i = 0; i < x.length; i++){
 	x[i].disabled = true
}
