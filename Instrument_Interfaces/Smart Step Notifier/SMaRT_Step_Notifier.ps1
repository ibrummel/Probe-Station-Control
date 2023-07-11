param ($sample="", $msg="", $to_addr="iab5dy@virginia.edu", $T=-999, $F=-999)

conda activate base
& python "C:\SMaRT_Step_Notifier\SMaRT_Step_Notifier.py" --sample $sample --msg $msg --to_addr $to_addr -T $T -F $F