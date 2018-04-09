for i in ../*;
  do python3 main.py --dir $i --sort-by character --file-op copy --md5 hard --multiple copies --do-reverse true --host nolife || exit 1;
done
