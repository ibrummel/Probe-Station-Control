param ($dir="Electrode_Images", $file, $T)

write-host $dir
conda activate base
& python "C:\SMaRT_Image_Capture\SMaRT_Image_Capture.py" --dir $dir --file $file -T $T