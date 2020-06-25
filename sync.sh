if [ "$1" = "--toserver205" ];
then
    rsync -avz --exclude-from '.gitignore' --exclude-from '.repoignore' . zdeploy@172.26.16.2:/home/zdeploy/AILab/duydv2/worker-as-service/
fi
if [ "$1" = "--toserver14" ];
then
    rsync -avz --exclude-from '.gitignore' --exclude-from '.repoignore' . zdeploy@10.40.34.14:/zserver/AI-projects/AILab/worker-as-service/
fi
if [ "$1" = "--toserver15" ];
then
    rsync -avz --exclude-from '.gitignore' --exclude-from '.repoignore' . zdeploy@10.40.34.15:/zserver/AI-projects/AILab/worker-as-service/
fi
if [ "$1" = "--toserver16" ];
then
    rsync -avz --exclude-from '.gitignore' --exclude-from '.repoignore' . zdeploy@10.40.34.16:/zserver/AI-projects/AILab/worker-as-service/
fi
if [ "$1" = "--toserver9" ];
then
    rsync -avz --exclude-from '.gitignore' --exclude-from '.repoignore' . zdeploy@10.30.80.9:/zserver/AI-projects/AILab/worker-as-service/
fi
if [ "$1" = "--toserver25" ];
then
    rsync -avz --exclude-from '.gitignore' --exclude-from '.repoignore' . root@10.30.80.25:/root/AILab/duydv2/worker-as-service/
fi
if [ "$1" = "--toserver918" ];
then
    rsync -avz --exclude-from '.gitignore' --exclude-from '.repoignore' . root@10.50.9.18:/root/AILab/duydv2/worker-as-service/
fi
if [ "$1" = "--toserver18" ];
then
    rsync -avz --exclude-from '.gitignore' --exclude-from '.repoignore' . zdeploy@10.40.34.18:/zserver/AI-projects/AILab/worker-as-service/
fi
if [ "$1" = "--toserver201" ];
then
    rsync -avz --exclude-from '.gitignore' --exclude-from '.repoignore' . zdeploy@10.40.34.201:/zserver/AI-projects/AILab/worker-as-service/
fi
if [ "$1" = "--toserver11" ];
then
    rsync -avz --exclude-from '.gitignore' --exclude-from '.repoignore' . zdeploy@10.40.34.11:/zserver/AI-projects/AILab/worker-as-service/
fi
if [ "$1" = "--toserver22" ];
then
    rsync -avz --exclude-from '.gitignore' --exclude-from '.repoignore' . zdeploy@10.40.34.22:/zserver/AI-projects/AILab/worker-as-service/
fi