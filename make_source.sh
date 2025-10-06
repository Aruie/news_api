find ./app -type f -not -path "*/__pycache__/*" -print0 | while IFS= read -r -d '' file; do
  echo "$file"
  echo "'''"
  cat "$file"
  echo
  echo "'''"
  echo
done > all_backend_source.txt