for i in ../*;
  do python3 main.py --dir $i --sort-by character --file-op move --md5 hard --multiple mixed --do-reverse true --host nolife || exit 1;
done
