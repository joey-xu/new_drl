python joint.py --environment=Reacher-v1 --model=gan --epochs=500 |tee ./experiments_data/Reacher_gan_1.txt &&
python joint.py --environment=Pusher-v0 --model=gan --epochs=500 |tee ./experiments_data/Pusher_gan_1.txt &&
python joint.py --environment=Thrower-v0 --model=gan --epochs=500 |tee ./experiments_data/Thrower_gan_1.txt &&
python joint.py --environment=Striker-v0 --model=gan --epochs=500 |tee ./experiments_data/Striker_gan_1.txt &&
python joint.py --environment=InvertedPendulum-v1 --model=gan --epochs=500 |tee ./experiments_data/InvertedPendulum_gan_1.txt &&
python joint.py --environment=InvertedDoublePendulum-v1 --model=gan --epochs=500 |tee ./experiments_data/InvertedDoublePendulum_gan_1.txt &&
python joint.py --environment=HalfCheetah-v1 --model=gan --epochs=500 |tee ./experiments_data/HalfCheetah_gan_1.txt &&
python joint.py --environment=Hopper-v1 --model=gan --epochs=500 |tee ./experiments_data/Hopper_gan_1.txt &&
python joint.py --environment=Swimmer-v1 --model=gan --epochs=500 |tee ./experiments_data/Swimmer_gan_1.txt &&
python joint.py --environment=Walker2d-v1 --model=gan --epochs=500 |tee ./experiments_data/Walker2d_gan_1.txt &&
python joint.py --environment=Ant-v1 --model=gan --epochs=500 |tee ./experiments_data/Ant_gan_1.txt &&
python joint.py --environment=Humanoid-v1 --model=gan --epochs=500 |tee ./experiments_data/Humanoid_gan_1.txt &&
python joint.py --environment=HumanoidStandup-v1 --model=gan --epochs=500 |tee ./experiments_data/HumanoidStandup_gan_1.txt
