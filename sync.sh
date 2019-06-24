if [ "$1" = "--toserver205" ];
then
    rsync -avz --exclude-from '.gitignore' --exclude-from '.repoignore' . zdeploy@10.205.16.10:/home/zdeploy/AILab/duydv2/worker-as-service/
fi
if [ "$1" = "--toserver15" ];
then
    rsync -avz --exclude-from '.gitignore' --exclude-from '.repoignore' . zdeploy@10.40.34.15:/zserver/AI-projects/AILab/worker-as-service/
fi